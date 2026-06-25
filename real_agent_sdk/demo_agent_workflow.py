from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Tuple

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from real_agent_sdk.agents import PlannerAgent, ReviewerAgent, SearchAgent, WriterAgent
from real_agent_sdk.context import WorkflowContext
from real_agent_sdk.event_model import MODEL_NAME
from real_agent_sdk.event_recorder import EventRecorder
from real_agent_sdk.siliconflow_client import SiliconFlowClient
from real_agent_sdk.sinks import build_sink


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a real Agent workflow and record AgentScope events")
    parser.add_argument("--task", required=True, help="User task for the Agent workflow")
    parser.add_argument("--sink", choices=["jsonl", "kafka", "both"], default="jsonl")
    parser.add_argument("--output", default="tmp/real_agent_events.jsonl")
    parser.add_argument("--kafka-bootstrap", default="middleware:9092")
    parser.add_argument("--kafka-topic", default="agent-events")
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--timeout", type=int, default=60, help="SiliconFlow request timeout in seconds")
    parser.add_argument("--max-tokens", type=int, default=512, help="Maximum completion tokens per LLM call")
    parser.add_argument("--force-retry", action="store_true", help="Force reviewer to emit retry and rerun writer/reviewer once")
    return parser


def run_workflow(args: argparse.Namespace) -> None:
    sink = build_sink(args.sink, args.output, args.kafka_bootstrap, args.kafka_topic)
    recorder = EventRecorder(sink, model_name=args.model)
    client = SiliconFlowClient(model=args.model, timeout=args.timeout, max_tokens=args.max_tokens)
    workflow = WorkflowContext()
    parent_run_id = None
    parent_agent_id = None
    state: Dict[str, str] = {}

    try:
        parent_run_id, parent_agent_id, failed = _run_agent(PlannerAgent(client, recorder), workflow, parent_run_id, parent_agent_id, args.task, state)
        if failed:
            return
        parent_run_id, parent_agent_id, failed = _run_agent(SearchAgent(client, recorder), workflow, parent_run_id, parent_agent_id, args.task, state)
        if failed:
            return
        parent_run_id, parent_agent_id, failed = _run_agent(WriterAgent(client, recorder), workflow, parent_run_id, parent_agent_id, args.task, state)
        if failed:
            return

        reviewer = ReviewerAgent(client, recorder)
        parent_run_id, parent_agent_id, failed, should_retry, retry_count = _run_reviewer(
            reviewer,
            workflow,
            parent_run_id,
            parent_agent_id,
            args.task,
            state,
            force_retry=args.force_retry,
            retry_count=0,
        )
        if failed:
            return
        if should_retry:
            parent_run_id, parent_agent_id, failed = _run_agent(
                WriterAgent(client, recorder),
                workflow,
                parent_run_id,
                parent_agent_id,
                args.task,
                state,
                retry_count=retry_count,
            )
            if failed:
                return
            _run_reviewer(
                reviewer,
                workflow,
                parent_run_id,
                parent_agent_id,
                args.task,
                state,
                force_retry=False,
                retry_count=retry_count,
            )
    finally:
        recorder.close()


def _run_agent(agent, workflow: WorkflowContext, parent_run_id, parent_agent_id, task: str, state: Dict[str, str], retry_count: int = 0) -> Tuple[str, str, bool]:
    ctx = workflow.new_run(agent.role, parent_run_id, parent_agent_id)
    result = agent.run(ctx, task, inputs=state, retry_count=retry_count)
    if not result.failed:
        state[agent.role] = result.content
    return ctx.run_id, ctx.agent_id, result.failed


def _run_reviewer(
    agent: ReviewerAgent,
    workflow: WorkflowContext,
    parent_run_id,
    parent_agent_id,
    task: str,
    state: Dict[str, str],
    *,
    force_retry: bool,
    retry_count: int,
):
    ctx = workflow.new_run(agent.role, parent_run_id, parent_agent_id)
    result = agent.run(ctx, task, inputs=state, retry_count=retry_count, force_retry=force_retry)
    if not result.failed:
        state[agent.role] = result.content
    return ctx.run_id, ctx.agent_id, result.failed, result.should_retry, result.retry_count


def main() -> None:
    args = build_parser().parse_args()
    run_workflow(args)
    if args.sink in {"jsonl", "both"}:
        print(f"wrote events to {args.output}")
    if args.sink in {"kafka", "both"}:
        print(f"sent events to Kafka topic {args.kafka_topic}")


if __name__ == "__main__":
    main()
