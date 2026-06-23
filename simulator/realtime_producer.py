from __future__ import annotations

import json
import time
from datetime import date
from typing import Iterable

from event_model import AgentEvent
from offline_generator import generate_workflow_events


def _producer(bootstrap_servers: str):
    try:
        from kafka import KafkaProducer
    except ImportError as exc:
        raise RuntimeError("kafka-python is required for realtime mode. Install simulator/requirements.txt") from exc
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
        linger_ms=50,
        retries=3,
    )


def stream_events(bootstrap_servers: str, topic: str, rate: int) -> None:
    producer = _producer(bootstrap_servers)
    sleep_seconds = 1.0 / max(rate, 1)
    today = date.today()
    try:
        while True:
            for event in generate_workflow_events(today, today):
                producer.send(topic, event.to_dict())
                time.sleep(sleep_seconds)
    finally:
        producer.flush()
        producer.close()


def print_events(events: Iterable[AgentEvent]) -> None:
    for event in events:
        print(json.dumps(event.to_dict(), ensure_ascii=False))

