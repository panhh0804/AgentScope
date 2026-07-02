from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from app.repositories.mysql_repo import MySQLAnalyticsRepository
from app.services import mock_data


class StatisticsService:
    def __init__(self) -> None:
        self.repo = MySQLAnalyticsRepository()

    def trend(self) -> List[Dict[str, Any]]:
        end = date.today()
        start = end - timedelta(days=29)
        rows = self.repo.analytics_trend(start, end) or mock_data.daily_metrics(start, end)
        return [self._normalize_row(row) for row in rows]

    def errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        rows = self.repo.get_error_distribution(limit) or self._mock_errors()
        total = sum(int(row.get("total_count") or row.get("error_count") or 0) for row in rows)
        normalized = []
        for row in rows:
            item = self._normalize_row(row)
            count = int(item.get("total_count") or item.get("error_count") or 0)
            item["total_count"] = count
            item["percentage"] = float(item.get("percentage") or (count / total if total else 0))
            normalized.append(item)
        return normalized

    def agent_stats(self) -> List[Dict[str, Any]]:
        end = date.today()
        start = end - timedelta(days=29)
        rows = self.repo.get_agent_stats(start, end) or mock_data.rankings(end)
        return [self._normalize_row(row) for row in rows]

    def _mock_errors(self) -> List[Dict[str, Any]]:
        rows = [
            ("Rate Limit", 128),
            ("API Timeout", 96),
            ("Context Window Exceeded", 58),
            ("Tool Call Failed", 36),
            ("Unknown", 21),
        ]
        total = sum(count for _, count in rows)
        return [
            {"error_type": error_type, "total_count": count, "percentage": round(count / total, 4)}
            for error_type, count in rows
        ]

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                normalized[key] = value.isoformat()
            elif isinstance(value, Decimal):
                normalized[key] = float(value)
            else:
                normalized[key] = value
        return normalized
