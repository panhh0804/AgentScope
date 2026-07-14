"""
workflow_generator.py —— AgentScope 模拟器的工作流与事件生成引擎

本模块是模拟器中最核心的逻辑实现。定义了 WorkflowGenerator 类，用来模拟真实的 Multi-Agent 会话。
根据选择的会话场景 (SCENARIOS，如正常成功、超时高延迟、LLM 调用异常超量、循环死锁、工具调用失败、重试机制等)，
自动生成一条树状结构的 Multi-Agent 协作调用链路：
  - 链路拓扑为: planner -> search -> analysis -> writer -> reviewer
  - 支持在此过程中模拟注入各类“数据质量缺陷（脏数据）”，如随机缺失字段、负数延迟、Token 计算不一致等
  - 自动管理每一步骤的时间差 (gap) 与时延 (latency)，保证时间线的严格合理性
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional, Sequence

from agents import AGENT_ROLES
from event_model import AgentEvent, estimate_cost
from id_generator import IdGenerator


# 模拟器支持的所有测试会话场景
SCENARIOS = {
    "mixed",          # 混合模式，轮流生成以下各种场景
    "success",        # 全部节点运行成功（基准测试场景）
    "agent_failed",   # 随机某一个 Agent 节点执行报错
    "tool_failed",    # 工具（web_search）调用失败
    "high_latency",   # 发生严重高时延超时
    "retry",          # Review 阶段触发自动重试机制
    "token_overuse",  # LLM 请求超出最大 Context Token 限制
    "loop",           # 发生死循环死锁
}


@dataclass
class WorkflowGenerator:
    """
    工作流生成引擎，通过业务场景控制，生成具有特定数据特征的 AgentEvent 流。
    """
    config: Dict[str, Any]
    seed: Optional[int] = None
    scenario: str = "mixed"

    def __post_init__(self) -> None:
        """
        初始化随机数发生器、ID 生成器以及混合引导序列。
        """
        if self.scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario: {self.scenario}")
        # 使用特定种子初始化 Random，以确保可复现性
        self.random = random.Random(self.seed)
        self.ids = IdGenerator.from_seed(self.seed)
        self.sim_config = self.config.get("simulator", {})
        # 用于混合模式下的轮循引导队列
        self._mixed_bootstrap = ["success", "agent_failed", "tool_failed", "retry", "high_latency", "token_overuse", "loop"]

    def generate_events(self, count: int, start_date: date, end_date: date) -> Iterator[AgentEvent]:
        """
        批量、惰性生成总数不少于 count 的事件，并散布在业务日期区间中。

        Args:
            count (int): 目标生成的事件总数上限
            start_date (date): 仿真起始业务日期
            end_date (date): 仿真结束业务日期

        Yields:
            Iterator[AgentEvent]: 惰性生成的 AgentEvent
        """
        for _ in range(count):
            start_time = self._offline_start_time(start_date, end_date)
            for event in self.generate_workflow(start_time):
                yield event

    def generate_realtime_events(self) -> Iterator[AgentEvent]:
        """
        实时流仿真：生成无尽的实时事件序列，以秒级真实速率在后台产生，并推进时钟。

        Yields:
            Iterator[AgentEvent]: 无限的事件流对象
        """
        cursor = datetime.now(timezone.utc)
        while True:
            for event in self.generate_workflow(cursor):
                cursor = self._parse_time(event.timestamp) + self._gap()
                yield event
            # 控制流速，使其不超前于当前真实的系统时间
            cursor = max(cursor, datetime.now(timezone.utc))

    def generate_workflow(self, start_time: datetime) -> List[AgentEvent]:
        """
        模拟一次完整的 Multi-Agent 协作会话流程（包括一系列的前后关联步骤）。

        Args:
            start_time (datetime): 仿真工作流开始的基础物理时间

        Returns:
            List[AgentEvent]: 本次会话流所派生出的所有按时间排序的原子事件列表
        """
        scenario = self._choose_scenario()
        roles = self._roles_for_scenario(scenario)
        # 如果是节点错误场景，则随机抽取一个不幸的角色执行失败逻辑
        failed_role = self.random.choice(AGENT_ROLES) if scenario == "agent_failed" else None
        trace_id = self.ids.new_id("trace")
        events: List[AgentEvent] = []
        cursor = start_time
        parent_run_id = None
        parent_agent_id = None
        retry_count = self.random.randint(3, 5) if scenario == "retry" else 0

        # 按计划角色链条顺序逐个节点生成调用
        for step, role in enumerate(roles, start=1):
            run_id = self.ids.new_id("run")
            agent_id = f"{role}_agent"
            # 依据权重与场景判断当前节点对应的特殊控制分支
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
            
            # 生成单个角色内部经历的一系列子事件组
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

            # 更新下一跳时间与父节点继承关联
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
        """
        生成一个具体 Agent 节点内部的所有生命周期原子事件（Start, Request, Response, Complete/Failed/Retry 以及工具调用）。
        """
        agent_id = f"{role}_agent"
        complete_time = start_time + timedelta(milliseconds=latency_ms)
        # 根据经验比例计算节点内部的 LLM 请求时间点与响应时间点，使其符合物理时间先后顺序
        request_time = self._between(start_time, complete_time, 0.20)
        response_time = self._between(start_time, complete_time, 0.55)
        
        events = [
            # 1. Agent 启动事件
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
            # 2. 发起大模型请求
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
            # 3. 接收大模型响应（计算 Token 消耗）
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

        # 4. 如果是 search 搜索节点，需要插入 Tool Call (工具检索) 相关的事件周期
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

        # 5. 组装终结/重试状态事件
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
        # 确保整体返回的原子事件按物理时间戳升序排序
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
        """
        工厂方法：实例化具体的 AgentEvent 实例。
        在其中，我们还会以特定比率注入脏数据（异常），用以验证数据清洗作业（DataX / Spark Clean）与质量校验体系是否工作正常。
        """
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

        evt_id = self.ids.new_id("evt")
        tr_id = trace_id
        r_id = run_id
        lat = latency_ms
        tot_tok = total_tokens

        # 概率性注入异常 1: 缺少核心标识主键（空字符串模拟异常）
        if self.random.random() < 0.015:
            choice = self.random.choice(["event_id", "trace_id", "run_id"])
            if choice == "event_id":
                evt_id = ""
            elif choice == "trace_id":
                tr_id = ""
            elif choice == "run_id":
                r_id = ""

        # 概率性注入异常 2: 负数时延数值异常
        if self.random.random() < 0.015:
            lat = -self.random.randint(100, 2000)

        # 概率性注入异常 3: Token 数量相加对不上不一致（total_tokens != prompt_tokens + completion_tokens）
        if event_type == "llm_response" and self.random.random() < 0.015:
            tot_tok = prompt_tokens + completion_tokens + self.random.choice([-10, 10, 20])

        return AgentEvent(
            event_id=evt_id,
            trace_id=tr_id,
            run_id=r_id,
            parent_run_id=parent_run_id,
            agent_id=f"{role}_agent",
            parent_agent_id=parent_agent_id,
            agent_role=role,
            event_type=event_type,
            status=status,
            timestamp=timestamp.isoformat(),
            latency_ms=lat,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=tot_tok,
            cost_usd=cost_usd,
            model_name=model_name,
            tool_name=tool_name,
            error_type=error_type,
            retry_count=retry_count,
            metadata_json=metadata or {},
        )

    def _choose_scenario(self) -> str:
        """
        根据策略选择本次要模拟执行的会话场景。
        """
        if self.scenario != "mixed":
            return self.scenario
        # 混合模式下，优先弹出队列前部的引导场景（保证每种场景都在初始化时生成过）
        if self._mixed_bootstrap:
            return self._mixed_bootstrap.pop(0)
        weights = self.sim_config.get("scenario_weights", {})
        names = list(weights.keys())
        values = list(weights.values())
        return self.random.choices(names, weights=values, k=1)[0]

    @staticmethod
    def _roles_for_scenario(scenario: str) -> List[str]:
        """
        返回当前仿真场景所需要的 Agent 串行链条。
        对于 retry（重试）与 loop（死循环）场景，追加了冗余节点用以触发特定的机制。
        """
        if scenario in {"loop", "retry"}:
            return ["planner", "search", "analysis", "writer", "reviewer", "writer", "reviewer"]
        return AGENT_ROLES.copy()

    def _offline_start_time(self, start_date: date, end_date: date) -> datetime:
        """
        在给定的时间区间内，随机散布生成一个开始时间戳（UTC时区）。
        """
        if end_date < start_date:
            raise ValueError("end-date must be greater than or equal to start-date")
        days = (end_date - start_date).days
        selected_day = start_date + timedelta(days=self.random.randint(0, days))
        seconds = self.random.randint(0, 86399)
        millis = self.random.randint(0, 999)
        start = datetime.combine(selected_day, datetime.min.time(), tzinfo=timezone.utc)
        return start + timedelta(seconds=seconds, milliseconds=millis)

    def _agent_latency(self, high: bool = False) -> int:
        """
        随机生成节点大模型调用的耗时时长。
        """
        cfg = self.sim_config.get("latency_ms", {})
        if high:
            return self.random.randint(int(cfg.get("high_min", 10000)), int(cfg.get("high_max", 30000)))
        return self.random.randint(int(cfg.get("normal_min", 300)), int(cfg.get("normal_max", 4500)))

    def _tool_latency(self) -> int:
        """
        随机生成外部工具执行耗时。
        """
        cfg = self.sim_config.get("latency_ms", {})
        return self.random.randint(int(cfg.get("tool_min", 100)), int(cfg.get("tool_max", 2500)))

    def _tokens(self, overuse: bool = False) -> tuple[int, int]:
        """
        随机产生 prompt 和 completion 所消耗的 Token 数。
        """
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
        """
        随机生成两个事件节点之间短暂的物理网络间隙时长。
        """
        timing = self.sim_config.get("timing", {})
        min_ms = int(timing.get("gap_min_ms", 50))
        max_ms = int(timing.get("gap_max_ms", 500))
        return timedelta(milliseconds=self.random.randint(min_ms, max_ms))

    @staticmethod
    def _between(start: datetime, end: datetime, ratio: float) -> datetime:
        """
        线性插值辅助函数：根据比例计算起始与结束时间点中间的某个时刻。
        """
        delta_ms = max(int((end - start).total_seconds() * 1000), 4)
        return start + timedelta(milliseconds=max(1, int(delta_ms * ratio)))

    @staticmethod
    def _parse_time(value: str) -> datetime:
        """
        将 ISO8601 字符串解析回 Datetime。
        """
        return datetime.fromisoformat(value)

    def _task_type(self) -> str:
        """
        随机分配一个仿真业务子任务类型标签。
        """
        return self.random.choice(["market_research", "paper_review", "risk_analysis", "technical_report"])
