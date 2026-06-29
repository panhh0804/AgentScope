from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List


AGENTS = ["planner", "search", "analysis", "writer", "reviewer"]


def realtime_overview() -> Dict:
    sec = datetime.now().second
    return {
        "running_tasks": 15 + sec % 10,
        "active_agents": 5,
        "events_per_minute": 120 + sec % 20,
        "success_rate": 0.92 + (sec % 5) * 0.01,
        "error_rate": 0.08 - (sec % 5) * 0.01,
        "avg_latency_ms": 1500 + (sec % 15) * 100,
        "token_total_5m": 45000 + sec * 200,
        "estimated_cost_5m": 0.08 + (sec % 10) * 0.002,
        "retry_tasks": sec % 4,
        "open_alerts": sec % 3,
        "update_time": datetime.now().isoformat(timespec="seconds"),
    }


def realtime_trend(minutes: int) -> List[Dict]:
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
    sec = datetime.now().second
    return [
        {
            "agent_id": f"{role}_agent",
            "agent_role": role,
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

    # Dynamically inject extra alerts periodically to make the real-time panel dynamic
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

