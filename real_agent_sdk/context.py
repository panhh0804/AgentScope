from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


@dataclass
class RunContext:
    trace_id: str
    run_id: str
    agent_role: str
    parent_run_id: Optional[str] = None
    parent_agent_id: Optional[str] = None

    @property
    def agent_id(self) -> str:
        return f"{self.agent_role}_agent"


class WorkflowContext:
    def __init__(self) -> None:
        self.trace_id = new_id("trace")

    def new_run(self, agent_role: str, parent_run_id: Optional[str], parent_agent_id: Optional[str]) -> RunContext:
        return RunContext(
            trace_id=self.trace_id,
            run_id=new_id("run"),
            agent_role=agent_role,
            parent_run_id=parent_run_id,
            parent_agent_id=parent_agent_id,
        )

