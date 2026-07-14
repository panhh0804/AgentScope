"""
event_model.py —— AgentScope 模拟器的事件数据模型层

本模块是整个模拟器的数据核心，定义了：
  1. 合法的事件类型集合 (EVENT_TYPES)
  2. 合法的状态值集合 (STATUS_VALUES)
  3. 工具函数：UTC 时间戳生成、ID 生成、LLM 调用费用估算
  4. 核心数据类 AgentEvent：代表一条 Agent 运行链路中的原子事件记录

依赖关系：
  - 被 workflow_generator.py 用于实例化每一条事件
  - 被 offline_generator.py 和 realtime_producer.py 用于序列化并写出
  - 被 self_check.py 用于验证数据质量
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional
from uuid import uuid4


# 所有合法的事件类型，涵盖 Agent 生命周期和 LLM/工具调用的各阶段
EVENT_TYPES = {
    "agent_start",       # Agent 开始执行
    "agent_complete",    # Agent 成功完成
    "agent_failed",      # Agent 执行失败（含超时、模型错误等）
    "llm_request",       # 向 LLM 发出请求
    "llm_response",      # 收到 LLM 响应（含 token 统计）
    "tool_call",         # 调用外部工具（如 web_search）
    "tool_result",       # 工具调用结果返回
    "retry",             # 重试事件（retry_count >= 1）
    "alert",             # 告警事件（预留，用于异常触发）
}

# 所有合法的状态值，描述事件当前所处的执行阶段
STATUS_VALUES = {"running", "success", "failed", "retry"}


def utc_now_iso() -> str:
    """
    返回当前 UTC 时间的 ISO 8601 格式字符串。

    Returns:
        str: 例如 '2024-01-15T08:30:00.123456+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """
    生成一个带前缀的随机唯一 ID，格式为 '{prefix}_{16位十六进制}'。

    Args:
        prefix (str): ID 前缀，例如 'trace'、'run'、'evt'

    Returns:
        str: 例如 'trace_a3f1b2c4d5e6f708'
    """
    return f"{prefix}_{uuid4().hex[:16]}"


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """
    根据 prompt/completion token 数估算 LLM 调用费用（美元）。
    演示定价：prompt=$0.0000015/token，completion=$0.0000020/token。

    Args:
        prompt_tokens (int): 输入 token 数量
        completion_tokens (int): 输出 token 数量

    Returns:
        float: 估算费用，精确到小数点后 6 位
    """
    # Demo pricing only. Keep the exact model pricing configurable in production.
    cost = Decimal(prompt_tokens) * Decimal("0.0000015")
    cost += Decimal(completion_tokens) * Decimal("0.0000020")
    return float(cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


@dataclass
class AgentEvent:
    """
    Agent 运行链路中的一条原子事件记录，是整个模拟器的核心数据单元。

    一个工作流由多个 Agent 依次执行，每个 Agent 产生多条事件，
    事件之间通过 trace_id / run_id / parent_run_id 形成树状调用链。

    Attributes:
        event_id: 事件唯一标识，格式 'evt_xxxxxxxxxxxxxxxx'
        trace_id: 整条调用链的唯一标识，一次用户请求对应一个 trace
        run_id: 单个 Agent 执行实例 of unique ID
        parent_run_id: 父 Agent 的 run_id，构成 Agent 调用树
        agent_id: Agent 实体标识，格式 '{role}_agent'
        parent_agent_id: 父 Agent 的 agent_id
        agent_role: Agent 角色名，取值见 agents.AGENT_ROLES
        event_type: 事件类型，取值见 EVENT_TYPES
        status: 事件状态，取值见 STATUS_VALUES
        timestamp: 事件发生时间（ISO 8601 格式）
        latency_ms: 事件耗时（毫秒）
        prompt_tokens: LLM 输入 token 数，仅 llm_response 事件非零
        completion_tokens: LLM 输出 token 数，仅 llm_response 事件非零
        total_tokens: prompt + completion 之和
        cost_usd: 本次 LLM 调用估算费用（美元）
        model_name: 使用的 LLM 模型名称
        tool_name: 工具调用名称，仅 tool_call/tool_result 事件非空
        error_type: 错误类型描述，仅失败事件非空
        retry_count: 已重试次数
        metadata_json: 附加元数据，包含 scenario、step、workflow 等信息
    """

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
    metadata_json: Dict[str, Any] = field(default_factory=dict)  # 避免可变默认参数共享问题

    def validate(self) -> None:
        """
        验证事件字段合法性，确保 event_type 和 status 均在白名单内。

        Raises:
            ValueError: 当 event_type 或 status 不在合法集合中时抛出
        """
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type: {self.event_type}")
        if self.status not in STATUS_VALUES:
            raise ValueError(f"unknown status: {self.status}")
        # Allow empty fields for anomaly simulation testing, so that dirty/anomaly data
        # can be successfully exported to the source database.
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        将事件序列化为字典，供 JSON 序列化或数据库写入使用。

        Returns:
            Dict[str, Any]: 包含所有字段 of smooth flat dict

        Raises:
            ValueError: 若字段不合法（来自 validate()）
        """
        self.validate()
        return asdict(self)
