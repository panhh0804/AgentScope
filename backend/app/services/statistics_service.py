"""
statistics_service.py —— AgentScope 数据指标分析汇总服务

本服务配合离线数据统计端，用于提取多维度的效能与异常评估指标。包括：
  1. 近 30 天任务成功率及延迟吞吐趋势分析 (trend)
  2. 系统异常错误类型及分布比例分析 (errors)
  3. 各个 Agent 的时延分布与分位数计算 (agent_stats)

同样设计了基于默认 DATA_MODE 的降级容灾设计。
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.repositories.mysql_repo import MySQLAnalyticsRepository
from app.services import mock_data


class StatisticsService:
    """
    提供给前端离线统计端的聚合报表与统计计算服务层。
    """
    def __init__(self) -> None:
        """
        初始化统计服务，建立数据库连接门面。
        """
        self.repo = MySQLAnalyticsRepository()

    def _data_mode(self) -> str:
        """
        获取当前数据模式环境配置。

        Returns:
            str: 'strict' or 'normal' (with fallback support)
        """
        return os.getenv("DATA_MODE", "normal")

    def trend(self) -> Dict[str, Any]:
        """
        计算并提供近 30 天每日运行趋势统计（包括成功数、失败数、平均及 P95 延迟、Token 和花费）。

        Returns:
            Dict[str, Any]: 包含趋势列表数据的标准协议字典
        """
        end = date.today()
        start = end - timedelta(days=29)
        rows = self.repo.analytics_trend(start, end)
        if rows:
            # 转换 Decimal 为 float 以保证 JSON 序列化顺畅
            data = [self._normalize_row(row) for row in rows]
            return {"data": data, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        mock_rows = mock_data.trend()
        data = [self._normalize_row(row) for row in mock_rows]
        return {"data": data, "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def errors(
        self,
        limit: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        计算各异常类型在全局错误中的所占条数与占比（分布统计）。

        Args:
            limit (int): 限制输出的错误类别数
            start_date (Optional[date]): 过滤的起始日期
            end_date (Optional[date]): 过滤的截止日期

        Returns:
            Dict[str, Any]: 统一协议响应，data 元素带有 percentage 分布率
        """
        rows = self.repo.get_error_distribution(limit, start_date, end_date)
        if rows:
            total = sum(int(row.get("total_count") or row.get("error_count") or 0) for row in rows)
            normalized = []
            for row in rows:
                item = self._normalize_row(row)
                count = int(item.get("total_count") or item.get("error_count") or 0)
                item["total_count"] = count
                # 动态补齐算得的百分比率
                item["percentage"] = float(item.get("percentage") or (count / total if total else 0))
                normalized.append(item)
            return {"data": normalized, "data_source": "mysql", "fallback": False, "reason": None}
        
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        
        # 降级获取 mock 错误分布
        mock_rows = self._mock_errors()
        total = sum(int(row.get("total_count") or row.get("error_count") or 0) for row in mock_rows)
        normalized = []
        for row in mock_rows:
            item = self._normalize_row(row)
            count = int(item.get("total_count") or item.get("error_count") or 0)
            item["total_count"] = count
            item["percentage"] = float(item.get("percentage") or (count / total if total else 0))
            normalized.append(item)
        return {"data": normalized, "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def agent_stats(self) -> Dict[str, Any]:
        """
        分析并统计各个 Agent 角色的执行性能指标（平均及 P95 延迟、花费、以及总消耗 Token）。

        Returns:
            Dict[str, Any]: 统一协议字典
        """
        end = date.today()
        start = end - timedelta(days=29)
        rows = self.repo.get_agent_stats(start, end)
        if rows:
            data = [self._normalize_row(row) for row in rows]
            return {"data": data, "data_source": "mysql", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "mysql", "fallback": False, "reason": "MySQL empty or unavailable"}
        mock_rows = mock_data.rankings(end)
        data = [self._normalize_row(row) for row in mock_rows]
        return {"data": data, "data_source": "mock", "fallback": True, "reason": "MySQL empty or unavailable"}

    def _mock_errors(self) -> List[Dict[str, Any]]:
        """
        降级辅助：生成系统常见错误类型的 Mock 分布条数。
        """
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
        """
        行属性规范化，确保所有值均能顺利执行 JSON dump：
          - Datetime / Date 对象转换为 ISO 字符串
          - Decimal 高精度对象转换为常规的 float
        """
        normalized: Dict[str, Any] = {}
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                normalized[key] = value.isoformat()
            elif isinstance(value, Decimal):
                normalized[key] = float(value)
            else:
                normalized[key] = value
        return normalized
