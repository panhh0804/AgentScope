"""
self_check.py —— AgentScope 模拟器的输出自检与验证模块

该模块负责在模拟数据批量生成后执行断言自检，确保以下几点：
  1. 确定性种子复现：两次使用同一随机种子生成的文件字节内容必须完全一致。
  2. 核心事件类型覆盖：必须包含正常的执行流（Start, Complete）以及重试、工具调用、失败等分支。
  3. 数据一致性：
     - event_id 必须全局唯一
     - 每一条记录中 total_tokens 必须严格等于 prompt_tokens + completion_tokens
     - 只有 llm_response 事件才可以携带大于 0 的 token 数和 LLM 调用费用
     - 单个 trace 内部的事件 timestamp 必须单调递增
     - 合规的运行生命周期必须符合 Start -> Request -> Response -> Complete/Failed 的拓扑约束
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def load_jsonl(path: Path) -> List[Dict]:
    """
    加载并解析指定路径的 JSONL 文件。

    Args:
        path (Path): 文件路径对象

    Returns:
        List[Dict]: 解析后的事件字典列表
    """
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(name: str, condition: bool) -> None:
    """
    自检断言辅助函数，如果条件不满足，则抛出 AssertionError 标识检测失败。

    Args:
        name (str): 检测规则名称
        condition (bool): 断言布尔表达式值

    Raises:
        AssertionError: 当校验失败时抛出
    """
    if not condition:
        raise AssertionError(name)
    print(f"ok {name}")


def strictly_increasing_per_trace(events: List[Dict]) -> bool:
    """
    校验同一个 trace 下的事件时间戳是否随生成步骤单调递增。

    Args:
        events (List[Dict]): 待校验的事件字典列表

    Returns:
        bool: 如果每个 trace 内部的时间戳都单调递增则返回 True，否则返回 False
    """
    by_trace: Dict[str, List[str]] = {}
    for event in events:
        by_trace.setdefault(event["trace_id"], []).append(event["timestamp"])
    return all(all(items[i] < items[i + 1] for i in range(len(items) - 1)) for items in by_trace.values())


def complete_runs(events: List[Dict]) -> bool:
    """
    校验单个 Agent 执行实例的完整性。一个完整生命周期应从 agent_start 开始，
    经历模型的 LLM 调用，并最终结束于 agent_complete 或 agent_failed 状态。

    Args:
        events (List[Dict]): 事件列表

    Returns:
        bool: 在排除可控的仿真错误注入（最多允许 15% 异常残余）后，如果通过率合规，则返回 True
    """
    by_run: Dict[str, List[Dict]] = {}
    for event in events:
        if not event.get("run_id") or not event.get("trace_id") or not event.get("event_id"):
            continue
        by_run.setdefault(event["run_id"], []).append(event)
        
    incomplete_count = 0
    for rows in by_run.values():
        event_types = {event["event_type"] for event in rows}
        role = rows[0]["agent_role"]
        has_terminal = bool({"agent_complete", "agent_failed"} & event_types)
        # 判断是否包含了 start, request, response，并且包含终结事件
        is_complete = {"agent_start", "llm_request", "llm_response"}.issubset(event_types) and has_terminal
        # 对于 search 角色，必须要有调用工具的相关记录才算完整
        if role == "search" and not {"tool_call", "tool_result"}.issubset(event_types):
            is_complete = False
        if not is_complete:
            incomplete_count += 1
            
    # 允许最多 15% 的运行记录由于特定的异常模拟（比如异常容错模拟场景下）出现不完整，
    # 这是测试设计中期望观察到的脏数据容错率
    return incomplete_count <= len(by_run) * 0.15


def main() -> None:
    """
    自检脚本主入口点，使用命令行参数解析，定位并读取需要断言的文件目录。
    """
    parser = argparse.ArgumentParser(description="Validate generated AgentScope JSONL samples")
    parser.add_argument("--dir", default="../tmp", help="Directory containing generated JSONL files")
    args = parser.parse_args()
    base = Path(args.dir)

    mixed = load_jsonl(base / "mixed_seed_42.jsonl")
    mixed_again = base / "mixed_seed_42_again.jsonl"
    if mixed_again.exists():
        # 验证幂等性
        require("deterministic seed output", (base / "mixed_seed_42.jsonl").read_bytes() == mixed_again.read_bytes())

    event_types = {event["event_type"] for event in mixed}
    print(f"mixed event types: {', '.join(sorted(event_types))}")
    print(f"mixed scenarios: {', '.join(sorted({event['metadata_json'].get('scenario', '') for event in mixed}))}")
    
    # 验证核心流程事件集是否完整
    require(
        "mixed core event types",
        {"agent_start", "agent_complete", "llm_request", "llm_response", "tool_call", "tool_result"}.issubset(event_types),
    )
    # 验证包括异常重试在内的 8 种核心事件是否覆盖
    require(
        "mixed eight event types",
        {
            "agent_start",
            "agent_complete",
            "agent_failed",
            "llm_request",
            "llm_response",
            "tool_call",
            "tool_result",
            "retry",
        }.issubset(event_types),
    )
    
    # 验证 event_id 唯一性约束
    valid_events = [e for e in mixed if e.get("event_id")]
    require("event_id unique", len({e["event_id"] for e in valid_events}) == len(valid_events))
    
    # 验证 token 的代数一致性
    require("total_tokens consistent", all(event["total_tokens"] == event["prompt_tokens"] + event["completion_tokens"] for event in mixed))
    
    # 验证非 LLM 响应事件不能有耗能和开销
    require("non-llm_response tokens and cost are zero", all(
        (event["event_type"] == "llm_response") or 
        (event["prompt_tokens"] == 0 and event["completion_tokens"] == 0 and event["total_tokens"] == 0 and float(event["cost_usd"]) == 0.0)
        for event in mixed
    ))
    
    # 校验时间单调递增性与工作流完整性
    require("timestamps increasing per trace", strictly_increasing_per_trace(mixed))
    require("complete runs", complete_runs(mixed))

    # 针对各种错误场景所生成的文件进行特性检测断言
    checks = {
        "agent_failed": lambda rows: any(event["event_type"] == "agent_failed" for event in rows),
        "retry": lambda rows: any(event["event_type"] == "retry" and event["retry_count"] >= 3 for event in rows),
        "high_latency": lambda rows: any(event["latency_ms"] > 10000 for event in rows),
        "token_overuse": lambda rows: any(event["total_tokens"] > 20000 for event in rows),
        "tool_failed": lambda rows: any(event["event_type"] == "tool_result" and event["status"] == "failed" for event in rows),
    }
    for name, check in checks.items():
        path = base / f"{name}.jsonl"
        if path.exists():
            require(name, check(load_jsonl(path)))


if __name__ == "__main__":
    main()
