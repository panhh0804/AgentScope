"""
metric_service.py —— AgentScope 离线数仓指标查询服务

本服务封装了对于离线数仓（MySQL Analytics 库）的各类聚合报表指标的查询逻辑，包括：
  1. 每日系统执行情况（daily_metrics）
  2. 单日每小时的趋势细分（hourly_metrics）
  3. 智能体效能排行榜（agent_rankings）
  4. 智能体调用链关联网络（agent_relations）
  5. 历史离线批处理告警列表（history_alerts）

设计原则：
  - 采用松耦合降级策略：默认情况下直接查询 MySQL，当库表为空或不可达时，
    依据 DATA_MODE 配置，如果是 strict 则返回空并报错，
    如果是 demo（默认值）则降级调用 mock_data 生成模拟指标展示，实现高可用。
"""

from __future__ import annotations

import os
from datetime import date
from typing import Dict, List

from app.repositories.mysql_repo import MySQLAnalyticsRepository
from app.services import mock_data


class MetricService:
    """
    离线多维分析度量服务类，负责前后端指标数据的查询调度。
    """
    def __init__(self) -> None:
        """
        初始化指标服务，绑定 MySQL 分析层仓储库。
        """
        self.repo = MySQLAnalyticsRepository()

    def _data_mode(self) -> str:
        """
        获取当前系统的数据模式配置。
        支持：
          - 'strict': 严格模式，只返回数据库真实数据，如数据库连接不上直接返回空
          - 'demo': 演示/开发模式，具备自动 mock 数据降级兜底

        Returns:
            str: 规范化的字符串模式
        """
        return os.getenv("DATA_MODE", "demo").lower()

    def daily_metrics(self, start_date: date, end_date: date) -> Dict:
        """
        查询每日批处理多维运行度量数据（如任务总量、成功率、时延等）。

        Args:
            start_date (date): 起始业务日期
            end_date (date): 截止业务日期

        Returns:
            Dict: 统一协议字典（含 data, data_source, fallback, reason）
        """
        res = self.repo.daily_metrics(start_date, end_date)
        if res:
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.daily_metrics(start_date, end_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def hourly_metrics(self, metric_date: date) -> Dict:
        """
        查询某一天中 24 小时的精细度运行流量指标。

        Args:
            metric_date (date): 查询的业务日期

        Returns:
            Dict: 统一协议字典
        """
        res = self.repo.hourly_metrics(metric_date)
        if res:
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.hourly_metrics(metric_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def agent_rankings(self, metric_date: date) -> Dict:
        """
        查询单日 Agent 效能利用效率排行榜。

        Args:
            metric_date (date): 业务日期

        Returns:
            Dict: 统一协议字典
        """
        res = self.repo.agent_rankings(metric_date)
        if res:
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.rankings(metric_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def agent_relations(self, metric_date: date) -> Dict:
        """
        查询 Agent 的关联调用拓扑图数据，用于大屏拓扑网络渲染。

        Args:
            metric_date (date): 业务日期

        Returns:
            Dict: 统一协议字典，data 内包含 nodes 与 links
        """
        res = self.repo.agent_relations(metric_date)
        if res and res.get("nodes") and res.get("links"):
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": {"nodes": [], "links": []}, "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.relation_graph(metric_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def history_alerts(self, metric_date: date) -> Dict:
        """
        获取指定日期已归档的历史批处理告警事件清单。

        Args:
            metric_date (date): 业务日期

        Returns:
            Dict: 统一协议字典
        """
        res = self.repo.history_alerts(metric_date)
        if res:
            return {"data": res, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        return {"data": mock_data.history_alerts(metric_date), "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}
