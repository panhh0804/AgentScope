from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from real_agent_sdk.event_model import AgentEvent


class EventSink:
    def write(self, event: AgentEvent) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return None


class JsonlSink(EventSink):
    def __init__(self, output: str) -> None:
        self.path = Path(output)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fp = self.path.open("w", encoding="utf-8")

    def write(self, event: AgentEvent) -> None:
        self.fp.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        self.fp.flush()

    def close(self) -> None:
        self.fp.close()


class KafkaSink(EventSink):
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        try:
            from kafka import KafkaProducer
        except ImportError as exc:
            raise RuntimeError("kafka-python is required for --sink kafka/both") from exc

        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            key_serializer=lambda value: value.encode("utf-8"),
            value_serializer=lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            linger_ms=50,
            retries=3,
        )

    def write(self, event: AgentEvent) -> None:
        self.producer.send(self.topic, key=event.trace_id, value=event.to_dict())

    def close(self) -> None:
        self.producer.flush()
        self.producer.close()


class MultiSink(EventSink):
    def __init__(self, sinks: Iterable[EventSink]) -> None:
        self.sinks = list(sinks)

    def write(self, event: AgentEvent) -> None:
        for sink in self.sinks:
            sink.write(event)

    def close(self) -> None:
        for sink in self.sinks:
            sink.close()


def build_sink(mode: str, output: Optional[str], kafka_bootstrap: str, kafka_topic: str) -> EventSink:
    if mode == "jsonl":
        if not output:
            raise ValueError("--output is required when --sink jsonl")
        return JsonlSink(output)
    if mode == "kafka":
        return KafkaSink(kafka_bootstrap, kafka_topic)
    if mode == "both":
        if not output:
            raise ValueError("--output is required when --sink both")
        return MultiSink([JsonlSink(output), KafkaSink(kafka_bootstrap, kafka_topic)])
    raise ValueError(f"unknown sink: {mode}")

