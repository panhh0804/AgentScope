from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from real_agent_sdk.event_model import MODEL_NAME, REQUIRED_FIELDS


def load_events(path: Path) -> List[Dict]:
    events = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise AssertionError(f"invalid JSON at line {lineno}: {exc}") from exc
    return events


def require(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"ok {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate real Agent SDK JSONL events")
    parser.add_argument("--file", required=True)
    parser.add_argument("--model", default=MODEL_NAME)
    args = parser.parse_args()

    events = load_events(Path(args.file))
    require("non-empty JSONL", bool(events))
    require("required fields", all(all(field in event for field in REQUIRED_FIELDS) for event in events))
    require("event_id unique", len({event["event_id"] for event in events}) == len(events))
    require("timestamps increasing per trace", timestamps_increasing(events))
    require("run terminal event", runs_have_terminal(events))
    require("llm request paired", llm_requests_paired(events))
    require("tool call paired", tool_calls_paired(events))
    require("token totals", all(event["total_tokens"] == event["prompt_tokens"] + event["completion_tokens"] for event in events))
    require("model name", all(event["model_name"] == args.model for event in events))
    require("metadata_json parseable", all(metadata_parseable(event["metadata_json"]) for event in events))


def timestamps_increasing(events: List[Dict]) -> bool:
    by_trace: Dict[str, List[str]] = defaultdict(list)
    for event in events:
        by_trace[event["trace_id"]].append(event["timestamp"])
    return all(all(items[i] < items[i + 1] for i in range(len(items) - 1)) for items in by_trace.values())


def runs_have_terminal(events: List[Dict]) -> bool:
    by_run = group_by_run(events)
    return all({"agent_complete", "agent_failed"} & {event["event_type"] for event in rows} for rows in by_run.values())


def llm_requests_paired(events: List[Dict]) -> bool:
    by_run = group_by_run(events)
    for rows in by_run.values():
        event_types = {event["event_type"] for event in rows}
        if "llm_request" in event_types and not ({"llm_response", "agent_failed"} & event_types):
            return False
    return True


def tool_calls_paired(events: List[Dict]) -> bool:
    by_run = group_by_run(events)
    for rows in by_run.values():
        event_types = {event["event_type"] for event in rows}
        if "tool_call" in event_types and "tool_result" not in event_types:
            return False
    return True


def metadata_parseable(value) -> bool:
    if isinstance(value, dict):
        return True
    if isinstance(value, str):
        try:
            json.loads(value)
            return True
        except json.JSONDecodeError:
            return False
    return False


def group_by_run(events: List[Dict]):
    by_run = defaultdict(list)
    for event in events:
        by_run[event["run_id"]].append(event)
    return by_run


if __name__ == "__main__":
    main()
