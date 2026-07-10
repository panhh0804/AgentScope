from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional
from uuid import uuid4


EVENT_TYPES = {
    "agent_start",
    "agent_complete",
    "agent_failed",
    "llm_request",
    "llm_response",
    "tool_call",
    "tool_result",
    "retry",
    "alert",
}

STATUS_VALUES = {"running", "success", "failed", "retry"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    # Demo pricing only. Keep the exact model pricing configurable in production.
    cost = Decimal(prompt_tokens) * Decimal("0.0000015")
    cost += Decimal(completion_tokens) * Decimal("0.0000020")
    return float(cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


@dataclass
class AgentEvent:
    event_id: str
    trace_id: str
    run_id: str
    parent_run_id: Optional[str]
    agent_id: str
    parent_agent_id: Optional[str]
    agent_role: str
    event_type: str
    status: str
    timestamp: str
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model_name: str = "gpt-4.1-mini"
    tool_name: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: int = 0
    metadata_json: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type: {self.event_type}")
        if self.status not in STATUS_VALUES:
            raise ValueError(f"unknown status: {self.status}")
        # Allow empty fields for anomaly simulation testing, so that dirty/anomaly data
        # can be successfully exported to the source database.
        pass

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

