"""
realtime.py —— 实时监控大屏数据 API 接口端点

主要接口：
  - GET /overview: 获取系统全局存活指标概览（吞吐、成功率、时延）以及组件健康矩阵。
  - GET /trend: 查询秒级实时波动的折线滑动窗口趋势序列。
  - GET /agents: 探测当前在线活动中的智能体运行负载。
  - GET /alerts: 列出实时大屏未被解决的瞬时系统异常报警清单。
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.services.realtime_service import RealtimeService

router = APIRouter()
service = RealtimeService()


@router.get("/overview")
def overview():
    """
    拉取监控中心最顶部核心大卡片指标以及底层集群拓扑组件（YARN、Kafka 等）存活矩阵。

    Returns:
        JSON: 统一协议包裹的实时概览对象
    """
    return ok(service.overview())


@router.get("/trend")
def trend(minutes: int = Query(default=60, ge=1, le=240)):
    """
    查询过去特定滑窗周期内（单位：分钟/秒点，默认 60）的实时吞吐与时延趋势。

    Args:
        minutes (int): 滑窗跨度大小（限制在 1-240 之间）

    Returns:
        JSON: 统一协议包裹的滑动趋势序列
    """
    return ok(service.trend(minutes))


@router.get("/agents")
def agents():
    """
    获取实时活动的智能体角色实例运行工作状态。

    Returns:
        JSON: 统一协议包裹的智能体在线数据
    """
    return ok(service.agents())


@router.get("/alerts")
def realtime_alerts():
    """
    查询最近大屏积压告警。

    Returns:
        JSON: 统一协议包裹的当前活动告警列表
    """
    return ok(service.alerts())
