from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional, Sequence

from agents import AGENT_ROLES
from event_model import AgentEvent, estimate_cost
from id_generator import IdGenerator


SCENARIOS = {"mixed", "success", "agent_failed", "tool_failed", "high_latency", "retry", "token_overuse", "loop"}


@dataclass
class WorkflowGenerator:
    config: Dict[str, Any]
    seed: Optional[int] = None
    scenario: str = "mixed"

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario: {self.scenario}")
        self.random = random.Random(self.seed)
        self.ids = IdGenerator.from_seed(self.seed)
        self.sim_config = self.config.get("simulator", {})
        self._mixed_bootstrap = ["success", "agent_failed", "tool_failed", "retry", "high_latency", "token_overuse", "loop"]

    def generate_events(self, count: int, start_date: date, end_date: date) -> Iterator[AgentEvent]:
        for _ in range(count):
            start_time = self._offline_start_time(start_date, end_date)
            for event in self.generate_workflow(start_time):
                yield event

    def generate_realtime_events(self) -> Iterator[AgentEvent]:
        cursor = datetime.now(timezone.utc)
        while True:
            for event in self.generate_workflow(cursor):
                cursor = self._parse_time(event.timestamp) + self._gap()
                yield event
            cursor = max(cursor, datetime.now(timezone.utc))

    def generate_workflow(self, start_time: datetime) -> List[AgentEvent]:
        scenario = self._choose_scenario()
        roles = self._roles_for_scenario(scenario)
        failed_role = self.random.choice(AGENT_ROLES) if scenario == "agent_failed" else None
        trace_id = self.ids.new_id("trace")
        events: List[AgentEvent] = []
        cursor = start_time
        parent_run_id = None
        parent_agent_id = None
        retry_count = self.random.randint(3, 5) if scenario == "retry" else 0

        for step, role in enumerate(roles, start=1):
            run_id = self.ids.new_id("run")
            agent_id = f"{role}_agent"
            role_failed = scenario == "agent_failed" and role == failed_role
            role_high_latency = scenario == "high_latency" and role in {"analysis", "writer"}
            role_token_overuse = scenario == "token_overuse" and role in {"analysis", "writer"}
            role_retry = scenario == "retry" and role == "reviewer" and step == 5
            metadata = {
                "scenario": scenario,
                "step": step,
                "workflow": "research_assistant",
                "task_type": self._task_type(),
            }

            agent_latency = self._agent_latency(high=role_high_latency)
            events.extend(
                self._agent_events(
                    trace_id=trace_id,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    role=role,
                    parent_agent_id=parent_agent_id,
                    start_time=cursor,
                    latency_ms=agent_latency,
                    metadata=metadata,
                    failed=role_failed,
                    retry=role_retry,
                    retry_count=retry_count,
                    token_overuse=role_token_overuse,
                    tool_failed=scenario == "tool_failed" and role == "search",
                )
            )

            cursor = self._parse_time(events[-1].timestamp) + self._gap()
            parent_run_id = run_id
            parent_agent_id = agent_id

        return events

    def _agent_events(
        self,
        *,
        trace_id: str,
        run_id: str,
        parent_run_id: Optional[str],
        role: str,
        parent_agent_id: Optional[str],
        start_time: datetime,
        latency_ms: int,
        metadata: Dict[str, Any],
        failed: bool,
        retry: bool,
        retry_count: int,
        token_overuse: bool,
        tool_failed: bool,
    ) -> List[AgentEvent]:
        agent_id = f"{role}_agent"
        complete_time = start_time + timedelta(milliseconds=latency_ms)
        request_time = self._between(start_time, complete_time, 0.20)
        response_time = self._between(start_time, complete_time, 0.55)
        events = [
            self._event(
                trace_id=trace_id,
                run_id=run_id,
                parent_run_id=parent_run_id,
                role=role,
                parent_agent_id=parent_agent_id,
                event_type="agent_start",
                status="running",
                timestamp=start_time,
                metadata=metadata,
            ),
            self._event(
                trace_id=trace_id,
                run_id=run_id,
                parent_run_id=parent_run_id,
                role=role,
                parent_agent_id=parent_agent_id,
                event_type="llm_request",
                status="running",
                timestamp=request_time,
                metadata=metadata,
            ),
            self._event(
                trace_id=trace_id,
                run_id=run_id,
                parent_run_id=parent_run_id,
                role=role,
                parent_agent_id=parent_agent_id,
                event_type="llm_response",
                status="success",
                timestamp=response_time,
                metadata=metadata,
                token_overuse=token_overuse,
            ),
        ]

        if role == "search":
            tool_call_time = self._between(start_time, complete_time, 0.70)
            tool_result_time = self._between(start_time, complete_time, 0.85)
            tool_error = self.random.choice(["tool_timeout", "tool_error"]) if tool_failed else None
            events.extend(
                [
                    self._event(
                        trace_id=trace_id,
                        run_id=run_id,
                        parent_run_id=parent_run_id,
                        role=role,
                        parent_agent_id=parent_agent_id,
                        event_type="tool_call",
                        status="running",
                        timestamp=tool_call_time,
                        tool_name="web_search",
                        metadata=metadata,
                    ),
                    self._event(
                        trace_id=trace_id,
                        run_id=run_id,
                        parent_run_id=parent_run_id,
                        role=role,
                        parent_agent_id=parent_agent_id,
                        event_type="tool_result",
                        status="failed" if tool_failed else "success",
                        timestamp=tool_result_time,
                        latency_ms=self._tool_latency(),
                        error_type=tool_error,
                        tool_name="web_search",
                        metadata=metadata,
                    ),
                ]
            )

        if failed:
            events.append(
                self._event(
                    trace_id=trace_id,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    role=role,
                    parent_agent_id=parent_agent_id,
                    event_type="agent_failed",
                    status="failed",
                    timestamp=complete_time,
                    latency_ms=latency_ms,
                    error_type=self.random.choice(["timeout", "model_error", "validation_error"]),
                    metadata=metadata,
                )
            )
        elif retry:
            retry_time = complete_time - timedelta(milliseconds=1)
            events.extend(
                [
                    self._event(
                        trace_id=trace_id,
                        run_id=run_id,
                        parent_run_id=parent_run_id,
                        role=role,
                        parent_agent_id=parent_agent_id,
                        event_type="retry",
                        status="retry",
                        timestamp=retry_time,
                        latency_ms=latency_ms,
                        retry_count=retry_count,
                        metadata=metadata,
                    ),
                    self._event(
                        trace_id=trace_id,
                        run_id=run_id,
                        parent_run_id=parent_run_id,
                        role=role,
                        parent_agent_id=parent_agent_id,
                        event_type="agent_complete",
                        status="success",
                        timestamp=complete_time,
                        latency_ms=latency_ms,
                        retry_count=retry_count,
                        metadata=metadata,
                    ),
                ]
            )
        else:
            events.append(
                self._event(
                    trace_id=trace_id,
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    role=role,
                    parent_agent_id=parent_agent_id,
                    event_type="agent_complete",
                    status="success",
                    timestamp=complete_time,
                    latency_ms=latency_ms,
                    retry_count=retry_count if retry_count and role in {"writer", "reviewer"} else 0,
                    metadata=metadata,
                    token_overuse=token_overuse,
                )
            )
        return sorted(events, key=lambda item: item.timestamp)

    def _event(
        self,
        *,
        trace_id: str,
        run_id: str,
        parent_run_id: Optional[str],
        role: str,
        parent_agent_id: Optional[str],
        event_type: str,
        status: str,
        timestamp: datetime,
        latency_ms: int = 0,
        retry_count: int = 0,
        error_type: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        token_overuse: bool = False,
    ) -> AgentEvent:
        if event_type == "llm_response":
            prompt_tokens, completion_tokens = self._tokens(overuse=token_overuse)
            total_tokens = prompt_tokens + completion_tokens
            cost_usd = estimate_cost(prompt_tokens, completion_tokens)
            model_name = self.sim_config.get("default_model", "gpt-4.1-mini")
        else:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            cost_usd = 0.0
            model_name = None

        return AgentEvent(
            event_id=self.ids.new_id("evt"),
            trace_id=trace_id,
            run_id=run_id,
            parent_run_id=parent_run_id,
            agent_id=f"{role}_agent",
            parent_agent_id=parent_agent_id,
            agent_role=role,
            event_type=event_type,
            status=status,
            timestamp=timestamp.isoformat(),
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            model_name=model_name,
            tool_name=tool_name,
            error_type=error_type,
            retry_count=retry_count,
            metadata_json=metadata or {},
        )

    def _choose_scenario(self) -> str:
        if self.scenario != "mixed":
            return self.scenario
        if self._mixed_bootstrap:
            return self._mixed_bootstrap.pop(0)
        weights = self.sim_config.get("scenario_weights", {})
        names = list(weights.keys())
        values = list(weights.values())
        return self.random.choices(names, weights=values, k=1)[0]

    @staticmethod
    def _roles_for_scenario(scenario: str) -> List[str]:
        if scenario in {"loop", "retry"}:
            return ["planner", "search", "analysis", "writer", "reviewer", "writer", "reviewer"]
        return AGENT_ROLES.copy()

    def _offline_start_time(self, start_date: date, end_date: date) -> datetime:
        if end_date < start_date:
            raise ValueError("end-date must be greater than or equal to start-date")
        days = (end_date - start_date).days
        selected_day = start_date + timedelta(days=self.random.randint(0, days))
        seconds = self.random.randint(0, 86399)
        millis = self.random.randint(0, 999)
        start = datetime.combine(selected_day, datetime.min.time(), tzinfo=timezone.utc)
        return start + timedelta(seconds=seconds, milliseconds=millis)

    def _agent_latency(self, high: bool = False) -> int:
        cfg = self.sim_config.get("latency_ms", {})
        if high:
            return self.random.randint(int(cfg.get("high_min", 10000)), int(cfg.get("high_max", 30000)))
        return self.random.randint(int(cfg.get("normal_min", 300)), int(cfg.get("normal_max", 4500)))

    def _tool_latency(self) -> int:
        cfg = self.sim_config.get("latency_ms", {})
        return self.random.randint(int(cfg.get("tool_min", 100)), int(cfg.get("tool_max", 2500)))

    def _tokens(self, overuse: bool = False) -> tuple[int, int]:
        cfg = self.sim_config.get("tokens", {})
        if overuse:
            return (
                self.random.randint(int(cfg.get("overuse_prompt_min", 12000)), int(cfg.get("overuse_prompt_max", 18000))),
                self.random.randint(int(cfg.get("overuse_completion_min", 8000)), int(cfg.get("overuse_completion_max", 12000))),
            )
        return (
            self.random.randint(int(cfg.get("prompt_min", 200)), int(cfg.get("prompt_max", 2500))),
            self.random.randint(int(cfg.get("completion_min", 200)), int(cfg.get("completion_max", 1800))),
        )

    def _gap(self) -> timedelta:
        timing = self.sim_config.get("timing", {})
        min_ms = int(timing.get("gap_min_ms", 50))
        max_ms = int(timing.get("gap_max_ms", 500))
        return timedelta(milliseconds=self.random.randint(min_ms, max_ms))

    @staticmethod
    def _between(start: datetime, end: datetime, ratio: float) -> datetime:
        delta_ms = max(int((end - start).total_seconds() * 1000), 4)
        return start + timedelta(milliseconds=max(1, int(delta_ms * ratio)))

    @staticmethod
    def _parse_time(value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _task_type(self) -> str:
        return self.random.choice(["market_research", "paper_review", "risk_analysis", "technical_report"])
