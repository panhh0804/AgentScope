"""
graph.py —— 智能体拓扑调用图 API 接口端点

主要接口：
  - GET /agent-relations: 接收指定日期参数，获取该日各 Agent 实体交互关联连线的拓扑 JSON。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.metric_service import MetricService

router = APIRouter()
service = MetricService()


@router.get("/agent-relations")
def agent_relations(date_value: date = Query(..., alias="date")):
    """
    检索特定业务日期的各智能体调用网络拓扑图结构。

    Args:
        date_value (date): 过滤的业务日期（别名为 date，例如 ?date=2026-07-14）

    Returns:
        JSON: 标准响应包裹的拓扑图对象（含 nodes 和 links 连线）
    """
    return ok(service.agent_relations(date_value))
