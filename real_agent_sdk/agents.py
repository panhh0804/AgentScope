from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from real_agent_sdk.context import RunContext
from real_agent_sdk.event_recorder import EventRecorder
from real_agent_sdk.siliconflow_client import SiliconFlowClient, SiliconFlowError
from real_agent_sdk.tool_wrapper import SearchTool


@dataclass
class AgentResult:
    content: str = ""
    failed: bool = False
    should_retry: bool = False
    retry_count: int = 0


class BaseAgent:
    role = "agent"

    def __init__(self, client: SiliconFlowClient, recorder: EventRecorder) -> None:
        self.client = client
        self.recorder = recorder

    @property
    def system_prompt(self) -> str:
        return "你是一个严谨的多智能体工作流节点，输出要简洁、具体、可执行。"

    def build_user_prompt(self, task: str, inputs: Dict) -> str:
        return task

    def run(self, ctx: RunContext, task: str, inputs: Optional[Dict] = None, retry_count: int = 0, force_retry: bool = False) -> AgentResult:
        inputs = inputs or {}
        metadata = self._metadata(task, retry_count)
        start = time.perf_counter()
        self.recorder.record(ctx, event_type="agent_start", status="running", retry_count=retry_count, metadata=metadata)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.build_user_prompt(task, inputs)},
        ]
        self.recorder.record(ctx, event_type="llm_request", status="running", retry_count=retry_count, metadata=metadata)
        try:
            response = self.client.chat(messages)
            self.recorder.record(
                ctx,
                event_type="llm_response",
                status="success",
                prompt_tokens=response["prompt_tokens"],
                completion_tokens=response["completion_tokens"],
                retry_count=retry_count,
                metadata=metadata,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            self.recorder.record(
                ctx,
                event_type="agent_complete",
                status="success",
                latency_ms=latency_ms,
                retry_count=retry_count,
                metadata=metadata,
            )
            return AgentResult(content=response["content"], retry_count=retry_count)
        except SiliconFlowError as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self.recorder.record(
                ctx,
                event_type="agent_failed",
                status="failed",
                latency_ms=latency_ms,
                error_type=exc.__class__.__name__,
                retry_count=retry_count,
                metadata={**metadata, "error_message": str(exc)[:500]},
            )
            return AgentResult(failed=True, retry_count=retry_count)

    def _metadata(self, task: str, retry_count: int) -> Dict:
        return {
            "workflow": "real_research_assistant",
            "task": task,
            "retry_count": retry_count,
            "provider": "siliconflow",
        }


class PlannerAgent(BaseAgent):
    role = "planner"

    @property
    def system_prompt(self) -> str:
        return "你是 Planner Agent，负责拆解用户任务并给出执行计划。"


class SearchAgent(BaseAgent):
    role = "search"

    def __init__(self, client: SiliconFlowClient, recorder: EventRecorder, tool: Optional[SearchTool] = None) -> None:
        super().__init__(client, recorder)
        self.tool = tool or SearchTool()

    @property
    def system_prompt(self) -> str:
        return "你是 Search Agent，负责根据计划提炼检索重点，并总结检索结果。"

    def run(self, ctx: RunContext, task: str, inputs: Optional[Dict] = None, retry_count: int = 0, force_retry: bool = False) -> AgentResult:
        inputs = inputs or {}
        metadata = self._metadata(task, retry_count)
        start = time.perf_counter()
        self.recorder.record(ctx, event_type="agent_start", status="running", retry_count=retry_count, metadata=metadata)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.build_user_prompt(task, inputs)},
        ]
        self.recorder.record(ctx, event_type="llm_request", status="running", retry_count=retry_count, metadata=metadata)
        try:
            response = self.client.chat(messages)
            self.recorder.record(
                ctx,
                event_type="llm_response",
                status="success",
                prompt_tokens=response["prompt_tokens"],
                completion_tokens=response["completion_tokens"],
                retry_count=retry_count,
                metadata=metadata,
            )
            tool_start = time.perf_counter()
            self.recorder.record(ctx, event_type="tool_call", status="running", tool_name=self.tool.name, retry_count=retry_count, metadata=metadata)
            tool_result = self.tool.call(response["content"])
            self.recorder.record(
                ctx,
                event_type="tool_result",
                status="success",
                latency_ms=int((time.perf_counter() - tool_start) * 1000),
                tool_name=self.tool.name,
                retry_count=retry_count,
                metadata={**metadata, "tool_result": tool_result},
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            self.recorder.record(ctx, event_type="agent_complete", status="success", latency_ms=latency_ms, retry_count=retry_count, metadata=metadata)
            return AgentResult(content=f"{response['content']}\n\n检索摘要：{tool_result['summary']}", retry_count=retry_count)
        except SiliconFlowError as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self.recorder.record(
                ctx,
                event_type="agent_failed",
                status="failed",
                latency_ms=latency_ms,
                error_type=exc.__class__.__name__,
                retry_count=retry_count,
                metadata={**metadata, "error_message": str(exc)[:500]},
            )
            return AgentResult(failed=True, retry_count=retry_count)

    def build_user_prompt(self, task: str, inputs: Dict) -> str:
        return f"用户任务：{task}\nPlanner 输出：{inputs.get('planner', '')}\n请给出检索重点。"


class WriterAgent(BaseAgent):
    role = "writer"

    @property
    def system_prompt(self) -> str:
        return "你是 Writer Agent，负责基于计划和检索内容生成结构化答案。"

    def build_user_prompt(self, task: str, inputs: Dict) -> str:
        return f"用户任务：{task}\n计划：{inputs.get('planner', '')}\n检索摘要：{inputs.get('search', '')}\n请生成答案。"


class ReviewerAgent(BaseAgent):
    role = "reviewer"

    @property
    def system_prompt(self) -> str:
        return "你是 Reviewer Agent，负责审核答案质量，并指出是否需要重写。"

    def build_user_prompt(self, task: str, inputs: Dict) -> str:
        return f"用户任务：{task}\n候选答案：{inputs.get('writer', '')}\n请审核是否满足任务要求。"

    def run(self, ctx: RunContext, task: str, inputs: Optional[Dict] = None, retry_count: int = 0, force_retry: bool = False) -> AgentResult:
        inputs = inputs or {}
        metadata = self._metadata(task, retry_count)
        start = time.perf_counter()
        self.recorder.record(ctx, event_type="agent_start", status="running", retry_count=retry_count, metadata=metadata)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.build_user_prompt(task, inputs)},
        ]
        self.recorder.record(ctx, event_type="llm_request", status="running", retry_count=retry_count, metadata=metadata)
        try:
            response = self.client.chat(messages)
            self.recorder.record(
                ctx,
                event_type="llm_response",
                status="success",
                prompt_tokens=response["prompt_tokens"],
                completion_tokens=response["completion_tokens"],
                retry_count=retry_count,
                metadata=metadata,
            )
            should_retry = force_retry
            next_retry_count = max(retry_count + 1, 3) if should_retry else retry_count
            if should_retry:
                self.recorder.record(
                    ctx,
                    event_type="retry",
                    status="retry",
                    retry_count=next_retry_count,
                    metadata={**metadata, "reason": "forced demo retry"},
                )
            latency_ms = int((time.perf_counter() - start) * 1000)
            self.recorder.record(
                ctx,
                event_type="agent_complete",
                status="success",
                latency_ms=latency_ms,
                retry_count=next_retry_count,
                metadata=metadata,
            )
            return AgentResult(content=response["content"], should_retry=should_retry, retry_count=next_retry_count)
        except SiliconFlowError as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self.recorder.record(
                ctx,
                event_type="agent_failed",
                status="failed",
                latency_ms=latency_ms,
                error_type=exc.__class__.__name__,
                retry_count=retry_count,
                metadata={**metadata, "error_message": str(exc)[:500]},
            )
            return AgentResult(failed=True, retry_count=retry_count)


def agent_chain() -> List[str]:
    return ["planner", "search", "writer", "reviewer"]

