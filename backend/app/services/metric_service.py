from __future__ import annotations

from datetime import date
from typing import Dict, List

from app.repositories.mysql_repo import MySQLAnalyticsRepository
from app.services import mock_data


class MetricService:
    def __init__(self) -> None:
        self.repo = MySQLAnalyticsRepository()

    def daily_metrics(self, start_date: date, end_date: date) -> List[Dict]:
        return self.repo.daily_metrics(start_date, end_date) or mock_data.daily_metrics(start_date, end_date)

    def hourly_metrics(self, metric_date: date) -> List[Dict]:
        return self.repo.hourly_metrics(metric_date) or mock_data.hourly_metrics(metric_date)

    def agent_rankings(self, metric_date: date) -> List[Dict]:
        return self.repo.agent_rankings(metric_date) or mock_data.rankings(metric_date)

    def agent_relations(self, metric_date: date) -> Dict:
        return self.repo.agent_relations(metric_date) or mock_data.relation_graph(metric_date)

    def history_alerts(self, metric_date: date) -> List[Dict]:
        return self.repo.history_alerts(metric_date) or mock_data.history_alerts(metric_date)

