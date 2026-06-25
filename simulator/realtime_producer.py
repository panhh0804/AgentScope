from __future__ import annotations

import json
import sys
import time
from typing import Dict, Iterable, Optional

from config_loader import DEFAULT_CONFIG
from event_model import AgentEvent
from workflow_generator import WorkflowGenerator


def _producer(bootstrap_servers: str):
    try:
        from kafka import KafkaProducer
    except ImportError as exc:
        raise RuntimeError("kafka-python is required for realtime mode. Install simulator/requirements.txt") from exc
    try:
        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            linger_ms=50,
            retries=3,
        )
    except Exception as exc:
        raise RuntimeError(f"failed to connect to Kafka bootstrap servers: {bootstrap_servers}") from exc


def stream_events(
    bootstrap_servers: str,
    topic: str,
    rate: int,
    *,
    config: Optional[Dict] = None,
    seed: Optional[int] = None,
    scenario: str = "mixed",
    stdout: bool = False,
) -> None:
    generator = WorkflowGenerator(config or DEFAULT_CONFIG, seed=seed, scenario=scenario)
    sleep_seconds = 1.0 / max(rate, 1)
    events = generator.generate_realtime_events()

    if stdout:
        for event in events:
            print(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True), flush=True)
            time.sleep(sleep_seconds)
        return

    producer = _producer(bootstrap_servers)
    try:
        for event in events:
            producer.send(topic, event.to_dict())
            time.sleep(sleep_seconds)
    finally:
        producer.flush()
        producer.close()


def print_events(events: Iterable[AgentEvent]) -> None:
    for event in events:
        print(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True))


def fatal(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)

