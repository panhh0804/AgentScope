from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Optional

from real_agent_sdk.context import RunContext, new_id
from real_agent_sdk.event_model import AgentEvent, MODEL_NAME, estimate_cost, utc_now
from real_agent_sdk.sinks import EventSink


class EventRecorder:
    def __init__(self, sink: EventSink, model_name: str = MODEL_NAME) -> None:
        self.sink = sink
        self.model_name = model_name
        self._last_timestamp = None

    def close(self) -> None:
        self.sink.close()

    def record(
        self,
        ctx: RunContext,
        *,
        event_type: str,
        status: str,
        latency_ms: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        tool_name: Optional[str] = None,
        error_type: Optional[str] = None,
        retry_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
        timestamp = self._next_timestamp().isoformat()
        total_tokens = prompt_tokens + completion_tokens
        event = AgentEvent(
            event_id=new_id("evt"),
            trace_id=ctx.trace_id,
            run_id=ctx.run_id,
            parent_run_id=ctx.parent_run_id,
            agent_id=ctx.agent_id,
            parent_agent_id=ctx.parent_agent_id,
            agent_role=ctx.agent_role,
            event_type=event_type,
            status=status,
            timestamp=timestamp,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=estimate_cost(prompt_tokens, completion_tokens),
            model_name=self.model_name,
            tool_name=tool_name,
            error_type=error_type,
            retry_count=retry_count,
            metadata_json=metadata or {},
        )
        self.sink.write(event)
        return event

    def _next_timestamp(self):
        now = utc_now()
        if self._last_timestamp is not None and now <= self._last_timestamp:
            now = self._last_timestamp + timedelta(microseconds=1)
        self._last_timestamp = now
        return now

