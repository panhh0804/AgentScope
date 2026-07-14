"""
metrics.py —— 多维指标度量查询 API 接口端点

主要接口：
  - GET /daily: 接收起止日期区间，获取每日的核心吞吐、延迟、成本概览指标。
  - GET /hourly: 接收特定日期，获取当天 24 小时更细密时间步粒度的流量分布。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.metric_service import MetricService

router = APIRouter()
service = MetricService()


@router.get("/daily")
def daily(start_date: date = Query(...), end_date: date = Query(...)):
    """
    拉取指定业务日期范围（start_date 到 end_date）内的每日离线指标大盘汇总。

    Args:
        start_date (date): 开始业务日期（?start_date=2026-07-01）
        end_date (date): 截止业务日期（?end_date=2026-07-07）

    Returns:
        JSON: 统一协议包裹的指标数据列表
    """
    return ok(service.daily_metrics(start_date, end_date))


@router.get("/hourly")
def hourly(date_value: date = Query(..., alias="date")):
    """
    查询单日内各小时时点（0~23点）的微观流量趋势。

    Args:
        date_value (date): 过滤的业务日期（别名为 date，例如 ?date=2026-07-14）

    Returns:
        JSON: 统一协议包裹的 24 个小时趋势数据
    """
    return ok(service.hourly_metrics(date_value))
