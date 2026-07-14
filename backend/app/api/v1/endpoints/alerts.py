"""
alerts.py —— 历史运维告警 API 接口端点

主要接口：
  - GET /history: 接收指定日期参数，获取该日已被数仓计算归档的历史警告异常列表。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.metric_service import MetricService

router = APIRouter()
service = MetricService()


@router.get("/history")
def history(date_value: date = Query(..., alias="date")):
    """
    根据给定的业务日期，检索已归档的历史批处理运维告警。

    Args:
        date_value (date): 过滤的业务日期（别名为 date，例如 ?date=2026-07-14）

    Returns:
        JSON: 标准响应协议包裹的告警记录列表
    """
    return ok(service.history_alerts(date_value))
