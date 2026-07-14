"""
id_generator.py —— AgentScope 模拟器的 ID 生成器模块

用于为调用链中的各类实体生成带前缀的 ID。
支持确定性模式（如果设定了 seed，则按照自增数字生成 ID，便于进行单元测试与可复现性分析），
或随机生成模式（使用 UUID 混合高16位编码生成，适合高并发生产级模拟）。
"""

from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Optional
from uuid import uuid4


class IdGenerator:
    """
    负责生成模拟器专用的唯一标识 ID (event_id, trace_id, run_id 等)
    """
    def __init__(self, deterministic: bool = False) -> None:
        """
        初始化 ID 生成器。

        Args:
            deterministic (bool): 是否为确定性自增 ID 模式。默认为 False，即随机 UUID 模式。
        """
        self.deterministic = deterministic
        self._counters: DefaultDict[str, int] = defaultdict(int)

    @classmethod
    def from_seed(cls, seed: Optional[int]) -> "IdGenerator":
        """
        通过 Seed 创建 ID 生成器实例。如果 seed 存在，则强行开启确定性模式。

        Args:
            seed (Optional[int]): 确定性生成的随机种子

        Returns:
            IdGenerator: 初始化完成的 ID 生成器实例
        """
        return cls(deterministic=seed is not None)

    def new_id(self, prefix: str) -> str:
        """
        根据指定的前缀生成唯一 ID。

        Args:
            prefix (str): ID 的前缀，例如 'trace'、'run'、'evt'

        Returns:
            str: 格式为 '{prefix}_{随机UUID值}' 或 '{prefix}_{自增序列号}'
        """
        if not self.deterministic:
            return f"{prefix}_{uuid4().hex[:16]}"
        self._counters[prefix] += 1
        return f"{prefix}_{self._counters[prefix]:08d}"
