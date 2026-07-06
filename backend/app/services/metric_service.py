from __future__ import annotations

import os
from datetime import date
from typing import Dict, List

from app.repositories.mysql_repo import MySQLAnalyticsRepository
from app.services import mock_data


class MetricService:
    def __init__(self) -> None:
        self.repo = MySQLAnalyticsRepository()

    def _data_mode(self) -> str:
        return os.getenv("DATA_MODE", "demo").lower()

    def daily_metrics(self, start_date: date, end_date: date) -> Dict:
        res = self.repo.daily_metrics(start_date, end_date)
        if res:
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.daily_metrics(start_date, end_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def hourly_metrics(self, metric_date: date) -> Dict:
        res = self.repo.hourly_metrics(metric_date)
        if res:
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.hourly_metrics(metric_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def agent_rankings(self, metric_date: date) -> Dict:
        res = self.repo.agent_rankings(metric_date)
        if res:
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.rankings(metric_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def agent_relations(self, metric_date: date) -> Dict:
        res = self.repo.agent_relations(metric_date)
        if res and res.get("nodes") and res.get("links"):
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": {"nodes": [], "links": []}, "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.relation_graph(metric_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def history_alerts(self, metric_date: date) -> Dict:
        res = self.repo.history_alerts(metric_date)
        if res:
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.history_alerts(metric_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

