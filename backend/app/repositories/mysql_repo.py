from __future__ import annotations

import os
from datetime import date
from typing import Dict, List, Optional


class MySQLAnalyticsRepository:
    def __init__(self) -> None:
        self._enabled = os.getenv("MYSQL_ANALYTICS_ENABLED", "0") == "1"

    def _connect(self):
        if not self._enabled:
            return None
        try:
            import pymysql

            return pymysql.connect(
                host=os.getenv("MYSQL_HOST", "middleware"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER", "agentscope"),
                password=os.getenv("MYSQL_PASSWORD", "agentscope_pass"),
                database=os.getenv("MYSQL_ANALYTICS_DB", "agentscope_analytics"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=1,
            )
        except Exception:
            return None

    def _query(self, sql: str, params: tuple) -> Optional[List[Dict]]:
        conn = self._connect()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        finally:
            conn.close()

    def daily_metrics(self, start_date: date, end_date: date) -> Optional[List[Dict]]:
        return self._query(
            "SELECT * FROM daily_metrics WHERE metric_date BETWEEN %s AND %s ORDER BY metric_date",
            (start_date, end_date),
        )

    def hourly_metrics(self, metric_date: date) -> Optional[List[Dict]]:
        return self._query(
            "SELECT * FROM hourly_metrics WHERE metric_date = %s ORDER BY hour",
            (metric_date,),
        )

    def agent_rankings(self, metric_date: date) -> Optional[List[Dict]]:
        return self._query(
            "SELECT * FROM agent_rankings WHERE metric_date = %s ORDER BY execution_count DESC",
            (metric_date,),
        )

    def agent_relations(self, metric_date: date) -> Optional[Dict]:
        nodes = self._query("SELECT * FROM agent_relation_nodes WHERE metric_date = %s", (metric_date,))
        links = self._query("SELECT * FROM agent_relation_edges WHERE metric_date = %s", (metric_date,))
        if nodes is None or links is None:
            return None
        return {"metric_date": metric_date.isoformat(), "nodes": nodes, "links": links}

    def history_alerts(self, metric_date: date) -> Optional[List[Dict]]:
        return self._query(
            "SELECT * FROM historical_alerts WHERE metric_date = %s ORDER BY created_at DESC",
            (metric_date,),
        )

