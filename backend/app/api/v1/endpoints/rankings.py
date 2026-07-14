"""
rankings.py —— Agent 效能利用率排行榜 API 接口端点

主要接口：
  - GET /agents: 接收指定日期参数，获取该日各 Agent 实体的调用执行频次、Token、成功率与时延排名榜。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.metric_service import MetricService

router = APIRouter()
service = MetricService()


@router.get("/agents")
def agent_rankings(date_value: date = Query(..., alias="date")):
    """
    获取选定日期的各智能体（如 Planner, Search 等）工作量及效能指标排名列表。

    Args:
        date_value (date): 过滤的业务日期（别名为 date，例如 ?date=2026-07-14）

    Returns:
        JSON: 统一协议包裹的 Agent 排行榜数据
    """
    return ok(service.agent_rankings(date_value))
