"""
mock_data.py —— AgentScope 数据指标模拟生成层 (Fallback / Mock Data Provider)

在系统尚未启动离线仿真、或者是后端组件（如 Kafka, MySQL）断开连接时，
本模块作为兜底方案，利用系统当前秒数和配置基准，动态产生以下场景的 Mock 仿真数据：
  1. 实时数据概览 (realtime_overview)
  2. 实时历史趋势 (realtime_trend)
  3. 实时智能体运行状态 (realtime_agents)
  4. 实时告警积压记录 (recent_alerts)
  5. 离线每日核心多维指标 (daily_metrics)
  6. 离线单日小时细粒度指标 (hourly_metrics)
  7. 单日 Agent 指标效能排行榜 (rankings)
  8. 调用关系网络拓扑图 (relation_graph)
  9. 批量历史告警数据 (history_alerts)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List


# 智能体标准角色清单
AGENTS = ["planner", "search", "analysis", "writer", "reviewer"]


def realtime_overview() -> Dict:
    """
    动态生成实时监控中心顶部的核心概览卡片数据。
    使用当前物理秒数 (datetime.now().second) 做取模运算，使数据在每次刷新时具备微弱波动性，营造真实演进的视觉效果。

    Returns:
        Dict: 包含运行中任务数、吞吐量、成功率、时延、消耗成本等度量指标的字典
    """
    sec = datetime.now().second
    return {
        "running_tasks": 15 + sec % 10,                 # 模拟 15-24 个并发执行的任务
        "active_agents": 5,                             # 固定 5 类智能体
        "events_per_minute": 120 + sec % 20,            # 模拟每分钟事件处理速率
        "success_rate": 0.92 + (sec % 5) * 0.01,        # 成功率在 92% ~ 96% 间抖动
        "error_rate": 0.08 - (sec % 5) * 0.01,          # 错误率与成功率互补
        "avg_latency_ms": 1500 + (sec % 15) * 100,      # 时延在 1.5s ~ 2.9s 之间波动
        "token_total_5m": 45000 + sec * 200,            # 最近 5 分钟 Token 消费累计量
        "estimated_cost_5m": 0.08 + (sec % 10) * 0.002, # 最近 5 分钟估算花费
        "retry_tasks": sec % 4,                         # 重试队列积压数
        "open_alerts": sec % 3,                         # 当前未解决的告警条数
        "update_time": datetime.now().isoformat(timespec="seconds"), # 本次渲染的时间截断
    }


def realtime_trend(minutes: int) -> List[Dict]:
    """
    生成过去一段时间内（比如最近 30 秒/分钟）的实时数据处理吞吐与耗时趋势点。

    Args:
        minutes (int): 指定需要生成的趋势点样本长度

    Returns:
        List[Dict]: 趋势数据列表，每个元素包含时间戳、事件数、成功数、失败数及平均耗时
    """
    seconds = minutes
    now = datetime.now()
    rows = []
    for idx in range(seconds):
        ts = now - timedelta(seconds=seconds - idx - 1)
        rows.append(
            {
                "time": ts.isoformat(timespec="seconds"),
                "events": 80 + (idx * 7) % 55,
                "success": 70 + (idx * 5) % 45,
                "failed": 3 + idx % 8,
                "avg_latency_ms": 1200 + (idx * 113) % 2200,
            }
        )
    return rows


def realtime_agents() -> List[Dict]:
    """
    生成当前各类型 Agent 的工作状态、实时成功率、累计 Token 及最新活跃时间。

    Returns:
        List[Dict]: 每个角色的实时度量字典列表
    """
    sec = datetime.now().second
    return [
        {
            "agent_id": f"{role}_agent",
            "agent_role": role,
            # 状态通过秒数动态切换，展示出 Agent 繁忙与闲置的更迭
            "status": "running" if (idx + sec // 5) % 2 == 0 else "idle",
            "current_task": f"trace_demo_{100 + (sec // 10):03d}",
            "success_rate": round(0.91 + ((idx + sec) % 7) * 0.012, 3),
            "avg_latency_ms": 900 + ((idx + sec) % 5) * 430,
            "token_total": 12000 + ((idx + sec) % 20) * 1800,
            "retry_count": (idx + sec // 15) % 3,
            "last_event_time": datetime.now().isoformat(timespec="seconds"),
        }
        for idx, role in enumerate(AGENTS)
    ]


def recent_alerts() -> List[Dict]:
    """
    生成实时告警大屏所需显示的异常告警事件（如：延迟超限、触发高频重试、限流等）。
    通过秒数在 15~45 秒内动态添加额外的严重告警项，使大屏幕在没有真实异常时也能产生交替告警。

    Returns:
        List[Dict]: 活动中的告警项列表
    """
    now = datetime.now()
    sec = now.second
    alerts = [
        {
            "alert_id": "alert_demo_latency",
            "alert_type": "high_latency",
            "level": "warning",
            "agent_id": "writer_agent",
            "current_value": 12800,
            "threshold": 10000,
            "source": "streaming",
            "status": "open",
            "create_time": (now - timedelta(minutes=3)).isoformat(timespec="seconds"),
        },
        {
            "alert_id": "alert_demo_retry",
            "alert_type": "frequent_retry",
            "level": "critical",
            "agent_id": "reviewer_agent",
            "current_value": 4,
            "threshold": 3,
            "source": "streaming",
            "status": "open",
            "create_time": (now - timedelta(minutes=6)).isoformat(timespec="seconds"),
        },
    ]

    # 当秒数在 [15, 45] 之间时，模拟注入大模型 HTTP 429 限流告警
    if 15 <= sec <= 45:
        alerts.append({
            "alert_id": "alert_demo_rate_limit",
            "alert_type": "rate_limit_exceeded",
            "level": "critical",
            "agent_id": "planner_agent",
            "current_value": 429,
            "threshold": 200,
            "source": "streaming",
            "status": "open",
            "create_time": (now - timedelta(seconds=sec - 15)).isoformat(timespec="seconds"),
        })

    # 当秒数大于 30 秒时，模拟注入 Token 溢出告警
    if sec > 30:
        alerts.append({
            "alert_id": "alert_demo_token_overflow",
            "alert_type": "token_limit",
            "level": "warning",
            "agent_id": "search_agent",
            "current_value": 8500,
            "threshold": 8000,
            "source": "streaming",
            "status": "open",
            "create_time": (now - timedelta(seconds=sec - 30)).isoformat(timespec="seconds"),
        })

    return alerts


def daily_metrics(start: date, end: date) -> List[Dict]:
    """
    提供每日离线数仓 ADS 级指标的 Mock 数据（含任务总量、成功率、时延、消耗成本等趋势）。

    Args:
        start (date): 查询起始日期
        end (date): 查询截止日期

    Returns:
        List[Dict]: 按天平铺的历史离线指标数据
    """
    days = (end - start).days + 1
    return [
        {
            "metric_date": (start + timedelta(days=idx)).isoformat(),
            "task_count": 1000 + idx * 82,
            "success_count": 920 + idx * 75,
            "failed_count": 80 + idx * 7,
            "success_rate": round(0.91 + (idx % 5) * 0.008, 3),
            "avg_latency_ms": 1600 + idx * 60,
            "p95_latency_ms": 4100 + idx * 90,
            "total_tokens": 1_200_000 + idx * 95_000,
            "estimated_cost_usd": round(2.4 + idx * 0.18, 4),
        }
        for idx in range(max(days, 0))
    ]


def hourly_metrics(metric_date: date) -> List[Dict]:
    """
    生成单日内以小时为维度的流量分布数据。

    Args:
        metric_date (date): 选定的业务日期

    Returns:
        List[Dict]: 一天 24 小时的指标序列
    """
    return [
        {
            "metric_date": metric_date.isoformat(),
            "hour": hour,
            "task_count": 36 + hour * 2,
            "success_rate": round(0.90 + (hour % 6) * 0.01, 3),
            "avg_latency_ms": 1100 + (hour * 137) % 1800,
            "total_tokens": 30000 + hour * 4200,
        }
        for hour in range(24)
    ]


def rankings(metric_date: date) -> List[Dict]:
    """
    生成指定日期的 Agent 执行效能排行榜单（按执行次数、Token、时延及花费）。

    Args:
        metric_date (date): 业务日期

    Returns:
        List[Dict]: 各 Agent 角色效能字典列表
    """
    return [
        {
            "metric_date": metric_date.isoformat(),
            "agent_id": f"{role}_agent",
            "agent_role": role,
            "execution_count": 1200 - idx * 95,
            "success_rate": round(0.94 - idx * 0.015, 3),
            "avg_latency_ms": 980 + idx * 520,
            "p95_latency_ms": 2600 + idx * 900,
            "total_tokens": 210000 + idx * 78000,
            "estimated_cost_usd": round(0.48 + idx * 0.17, 4),
        }
        for idx, role in enumerate(AGENTS)
    ]


def relation_graph(metric_date: date) -> Dict:
    """
    生成指定日期的智能体调用关系网路拓扑数据（包含节点及连线关系流量）。

    Args:
        metric_date (date): 业务日期

    Returns:
        Dict: 含有 nodes（节点列表）与 links（带权重边列表）的拓扑关系字典
    """
    nodes = [
        {"id": f"{role}_agent", "name": role.title(), "value": 100 - idx * 9}
        for idx, role in enumerate(AGENTS)
    ]
    links = [
        {
            "source": f"{AGENTS[idx]}_agent",
            "target": f"{AGENTS[idx + 1]}_agent",
            "call_count": 900 - idx * 70,
            "avg_latency_ms": 1200 + idx * 330,
            "failed_count": idx * 8,
            "total_tokens": 80000 + idx * 32000,
        }
        for idx in range(len(AGENTS) - 1)
    ]
    return {"metric_date": metric_date.isoformat(), "nodes": nodes, "links": links}


def history_alerts(metric_date: date) -> List[Dict]:
    """
    生成历史批处理告警的测试数据。

    Args:
        metric_date (date): 业务日期

    Returns:
        List[Dict]: 历史告警字典列表
    """
    return [
        {
            "alert_id": f"hist_{metric_date.isoformat()}_{idx}",
            "metric_date": metric_date.isoformat(),
            "alert_type": alert_type,
            "level": level,
            "agent_id": agent,
            "current_value": current,
            "threshold": threshold,
            "source": "batch",
            "status": "open",
        }
        for idx, (alert_type, level, agent, current, threshold) in enumerate(
            [
                ("high_error_rate", "warning", "search_agent", 0.24, 0.20),
                ("high_p95_latency", "warning", "writer_agent", 12400, 10000),
                ("high_cost_task", "info", "analysis_agent", 0.72, 0.50),
            ]
        )
    ]
