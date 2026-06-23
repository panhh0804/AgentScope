from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

from agents import AGENT_ROLES
from event_model import AgentEvent, estimate_cost, new_id
from scenarios import SCENARIO_WEIGHTS


def _random_timestamp(start_date: date, end_date: date) -> str:
    days = max((end_date - start_date).days, 0)
    selected_day = start_date + timedelta(days=random.randint(0, days))
    seconds = random.randint(0, 86399)
    dt = datetime.combine(selected_day, datetime.min.time(), tzinfo=timezone.utc)
    return (dt + timedelta(seconds=seconds)).isoformat()


def _choose_scenario() -> str:
    names = list(SCENARIO_WEIGHTS.keys())
    weights = list(SCENARIO_WEIGHTS.values())
    return random.choices(names, weights=weights, k=1)[0]


def _event(
    *,
    trace_id: str,
    run_id: str,
    parent_run_id: Optional[str],
    agent_role: str,
    parent_agent_id: Optional[str],
    event_type: str,
    status: str,
    timestamp: str,
    latency_ms: int = 0,
    retry_count: int = 0,
    error_type: Optional[str] = None,
    tool_name: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AgentEvent:
    prompt_tokens = random.randint(200, 2500)
    completion_tokens = random.randint(200, 1800)
    if metadata and metadata.get("token_overuse"):
        prompt_tokens = random.randint(12000, 18000)
        completion_tokens = random.randint(8000, 12000)
    total_tokens = prompt_tokens + completion_tokens
    return AgentEvent(
        event_id=new_id("evt"),
        trace_id=trace_id,
        run_id=run_id,
        parent_run_id=parent_run_id,
        agent_id=f"{agent_role}_agent",
        parent_agent_id=parent_agent_id,
        agent_role=agent_role,
        event_type=event_type,
        status=status,
        timestamp=timestamp,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=estimate_cost(prompt_tokens, completion_tokens),
        tool_name=tool_name,
        error_type=error_type,
        retry_count=retry_count,
        metadata_json=metadata or {},
    )


def generate_workflow_events(start_date: date, end_date: date) -> List[AgentEvent]:
    trace_id = new_id("trace")
    scenario = _choose_scenario()
    events: List[AgentEvent] = []
    parent_run_id = None
    parent_agent_id = None

    roles = AGENT_ROLES.copy()
    if scenario == "loop":
        roles.extend(["writer", "reviewer", "writer", "reviewer"])

    for idx, role in enumerate(roles):
        run_id = new_id("run")
        ts = _random_timestamp(start_date, end_date)
        retry_count = 0
        latency_ms = random.randint(300, 4500)
        error_type = None
        status = "success"
        event_type = "agent_complete"
        metadata = {"scenario": scenario, "step": idx + 1}

        if scenario == "high_latency" and role in {"analysis", "writer"}:
            latency_ms = random.randint(10000, 30000)
        if scenario == "retry" and role == "writer":
            retry_count = random.randint(3, 5)
            status = "retry"
            event_type = "retry"
        if scenario == "token_overuse" and role in {"analysis", "writer"}:
            metadata["token_overuse"] = True
        if scenario == "agent_failed" and role == random.choice(roles):
            status = "failed"
            event_type = "agent_failed"
            error_type = random.choice(["timeout", "model_error", "validation_error"])

        events.append(
            _event(
                trace_id=trace_id,
                run_id=run_id,
                parent_run_id=parent_run_id,
                agent_role=role,
                parent_agent_id=parent_agent_id,
                event_type="agent_start",
                status="running",
                timestamp=ts,
                metadata=metadata,
            )
        )

        if role == "search":
            tool_error = scenario == "tool_failed"
            events.append(
                _event(
                    trace_id=trace_id,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    agent_role=role,
                    parent_agent_id=parent_agent_id,
                    event_type="tool_result",
                    status="failed" if tool_error else "success",
                    timestamp=ts,
                    latency_ms=random.randint(100, 2500),
                    error_type="tool_timeout" if tool_error else None,
                    tool_name="web_search",
                    metadata=metadata,
                )
            )

        events.append(
            _event(
                trace_id=trace_id,
                run_id=run_id,
                parent_run_id=parent_run_id,
                agent_role=role,
                parent_agent_id=parent_agent_id,
                event_type=event_type,
                status=status,
                timestamp=ts,
                latency_ms=latency_ms,
                retry_count=retry_count,
                error_type=error_type,
                metadata=metadata,
            )
        )

        parent_run_id = run_id
        parent_agent_id = f"{role}_agent"

    return events


def generate_events(count: int, start_date: date, end_date: date) -> Iterator[AgentEvent]:
    emitted = 0
    while emitted < count:
        for event in generate_workflow_events(start_date, end_date):
            if emitted >= count:
                return
            emitted += 1
            yield event


def write_jsonl(events: Iterable[AgentEvent], output: str) -> int:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fp:
        for event in events:
            fp.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def write_mysql(events: Iterable[AgentEvent], host: str, port: int, user: str, password: str, database: str) -> int:
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("PyMySQL is required for MySQL output. Install simulator/requirements.txt") from exc

    sql = """
    INSERT INTO agent_events_source (
      event_id, trace_id, run_id, parent_run_id, agent_id, parent_agent_id,
      agent_role, event_type, status, event_time, latency_ms,
      prompt_tokens, completion_tokens, total_tokens, cost_usd, model_name,
      tool_name, error_type, retry_count, metadata_json
    ) VALUES (
      %(event_id)s, %(trace_id)s, %(run_id)s, %(parent_run_id)s, %(agent_id)s, %(parent_agent_id)s,
      %(agent_role)s, %(event_type)s, %(status)s, %(timestamp)s, %(latency_ms)s,
      %(prompt_tokens)s, %(completion_tokens)s, %(total_tokens)s, %(cost_usd)s, %(model_name)s,
      %(tool_name)s, %(error_type)s, %(retry_count)s, %(metadata_json)s
    )
    ON DUPLICATE KEY UPDATE status = VALUES(status), latency_ms = VALUES(latency_ms)
    """

    rows = []
    for event in events:
        item = event.to_dict()
        item["timestamp"] = item["timestamp"].replace("T", " ").split("+")[0]
        item["metadata_json"] = json.dumps(item["metadata_json"], ensure_ascii=False)
        rows.append(item)

    if not rows:
        return 0

    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset="utf8mb4")
    try:
        with conn.cursor() as cursor:
            cursor.executemany(sql, rows)
        conn.commit()
        return len(rows)
    finally:
        conn.close()
