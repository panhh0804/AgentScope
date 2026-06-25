from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

from config_loader import DEFAULT_CONFIG
from event_model import AgentEvent
from workflow_generator import WorkflowGenerator


def generate_workflow_events(
    start_date: date,
    end_date: date,
    *,
    config: Optional[Dict] = None,
    seed: Optional[int] = None,
    scenario: str = "mixed",
) -> list[AgentEvent]:
    generator = WorkflowGenerator(config or DEFAULT_CONFIG, seed=seed, scenario=scenario)
    start_time = generator._offline_start_time(start_date, end_date)
    return generator.generate_workflow(start_time)


def generate_events(
    count: int,
    start_date: date,
    end_date: date,
    *,
    config: Optional[Dict] = None,
    seed: Optional[int] = None,
    scenario: str = "mixed",
) -> Iterator[AgentEvent]:
    generator = WorkflowGenerator(config or DEFAULT_CONFIG, seed=seed, scenario=scenario)
    yield from generator.generate_events(count, start_date, end_date)


def write_jsonl(events: Iterable[AgentEvent], output: str) -> int:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fp:
        for event in events:
            fp.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
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
        item["metadata_json"] = json.dumps(item["metadata_json"], ensure_ascii=False, sort_keys=True)
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

