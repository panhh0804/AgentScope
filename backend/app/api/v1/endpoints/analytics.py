"""
analytics.py —— 离线多维分析度量 API 接口端点

主要接口：
  - GET /trend: 获取近 30 天每日运行概览（量级、时延、花费等）趋势指标。
  - GET /errors: 查询特定的错误分布情况（条数、异常百分比率）。
  - GET /agent-stats: 统计各 Agent 角色的分位数延迟与使用量指标。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.statistics_service import StatisticsService

router = APIRouter()
service = StatisticsService()


@router.get("/trend")
def trend():
    """
    拉取过去 30 天离线计算的任务流量及耗时变化趋势。

    Returns:
        JSON: 标准响应协议包裹的趋势指标列表
    """
    return ok(service.trend())


@router.get("/errors")
def errors(
    limit: int = Query(10, ge=1, le=50),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    """
    查询历史系统出现的异常错误类型的频次占比分布。

    Args:
        limit (int): 返回前多少个错误条目（限制在 1-50 之间，默认 10）
        start_date (Optional[date]): 起始过滤业务日期
        end_date (Optional[date]): 截止过滤业务日期

    Returns:
        JSON: 标准协议包裹的错误分布序列
    """
    return ok(service.errors(limit, start_date, end_date))


@router.get("/agent-stats")
def agent_stats():
    """
    按智能体分组，统计近期的平均与分位数时延耗时。

    Returns:
        JSON: 标准协议包裹的智能体分析统计
    """
    return ok(service.agent_stats())
