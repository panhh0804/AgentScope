from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def load_jsonl(path: Path) -> List[Dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"ok {name}")


def strictly_increasing_per_trace(events: List[Dict]) -> bool:
    by_trace: Dict[str, List[str]] = {}
    for event in events:
        by_trace.setdefault(event["trace_id"], []).append(event["timestamp"])
    return all(all(items[i] < items[i + 1] for i in range(len(items) - 1)) for items in by_trace.values())


def complete_runs(events: List[Dict]) -> bool:
    by_run: Dict[str, List[Dict]] = {}
    for event in events:
        by_run.setdefault(event["run_id"], []).append(event)
    for rows in by_run.values():
        event_types = {event["event_type"] for event in rows}
        role = rows[0]["agent_role"]
        has_terminal = bool({"agent_complete", "agent_failed"} & event_types)
        if not {"agent_start", "llm_request", "llm_response"}.issubset(event_types) or not has_terminal:
            return False
        if role == "search" and not {"tool_call", "tool_result"}.issubset(event_types):
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate generated AgentScope JSONL samples")
    parser.add_argument("--dir", default="../tmp", help="Directory containing generated JSONL files")
    args = parser.parse_args()
    base = Path(args.dir)

    mixed = load_jsonl(base / "mixed_seed_42.jsonl")
    mixed_again = base / "mixed_seed_42_again.jsonl"
    if mixed_again.exists():
        require("deterministic seed output", (base / "mixed_seed_42.jsonl").read_bytes() == mixed_again.read_bytes())

    event_types = {event["event_type"] for event in mixed}
    print(f"mixed event types: {', '.join(sorted(event_types))}")
    print(f"mixed scenarios: {', '.join(sorted({event['metadata_json'].get('scenario', '') for event in mixed}))}")
    require(
        "mixed core event types",
        {"agent_start", "agent_complete", "llm_request", "llm_response", "tool_call", "tool_result"}.issubset(event_types),
    )
    require(
        "mixed eight event types",
        {
            "agent_start",
            "agent_complete",
            "agent_failed",
            "llm_request",
            "llm_response",
            "tool_call",
            "tool_result",
            "retry",
        }.issubset(event_types),
    )
    require("event_id unique", len({event["event_id"] for event in mixed}) == len(mixed))
    require("total_tokens consistent", all(event["total_tokens"] == event["prompt_tokens"] + event["completion_tokens"] for event in mixed))
    require("timestamps increasing per trace", strictly_increasing_per_trace(mixed))
    require("complete runs", complete_runs(mixed))

    checks = {
        "agent_failed": lambda rows: any(event["event_type"] == "agent_failed" for event in rows),
        "retry": lambda rows: any(event["event_type"] == "retry" and event["retry_count"] >= 3 for event in rows),
        "high_latency": lambda rows: any(event["latency_ms"] > 10000 for event in rows),
        "token_overuse": lambda rows: any(event["total_tokens"] > 20000 for event in rows),
        "tool_failed": lambda rows: any(event["event_type"] == "tool_result" and event["status"] == "failed" for event in rows),
    }
    for name, check in checks.items():
        path = base / f"{name}.jsonl"
        if path.exists():
            require(name, check(load_jsonl(path)))


if __name__ == "__main__":
    main()
