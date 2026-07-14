"""
config_loader.py —— AgentScope 模拟器的配置加载层

该模块负责定义整个模拟器的默认参数体系（Kafka 拓扑、MySQL 账户密码、各种模拟场景及其时延和 Token 浮动区间），
并支持从外部的 YAML 文件加载配置，最终通过 deep_merge 算法与默认参数做深度合并。
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional


# 默认的模拟器全局配置，包含 Kafka、MySQL 的连接参数，以及事件延迟、Token 等特性的范围定义
DEFAULT_CONFIG: Dict[str, Any] = {
    "kafka": {
        "bootstrap_servers": "middleware:9092",
        "topic": "agent-events",
    },
    "mysql": {
        "host": "middleware",
        "port": 3306,
        "user": "agentscope",
        "password": "agentscope_pass",
        "database": "agentscope_source",
    },
    "simulator": {
        "default_rate": 10,
        "default_model": "gpt-4.1-mini",
        # 各种业务场景的模拟生成权重分配
        "scenario_weights": {
            "success": 70,          # 成功案例
            "agent_failed": 10,     # Agent 失败
            "tool_failed": 5,       # 工具失败
            "high_latency": 5,      # 超时/高延迟
            "retry": 5,             # 触发重试
            "token_overuse": 3,     # Token 超量异常
            "loop": 2,              # 循环死锁（非真实循环，模拟现象）
        },
        # 时延范围定义（毫秒）
        "latency_ms": {
            "normal_min": 300,
            "normal_max": 4500,
            "high_min": 10000,
            "high_max": 30000,
            "tool_min": 100,
            "tool_max": 2500,
        },
        # Token 数量浮动定义
        "tokens": {
            "prompt_min": 200,
            "prompt_max": 2500,
            "completion_min": 200,
            "completion_max": 1800,
            # 用于触发超量警告/异常的 Token 大小
            "overuse_prompt_min": 12000,
            "overuse_prompt_max": 18000,
            "overuse_completion_min": 8000,
            "overuse_completion_max": 12000,
        },
        # 步骤间的时间间隔（毫秒）
        "timing": {
            "gap_min_ms": 50,
            "gap_max_ms": 500,
        },
    },
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典，以递归方式用 override 覆盖 base 中的内容。

    Args:
        base (Dict[str, Any]): 基础配置字典
        override (Dict[str, Any]): 覆盖配置字典

    Returns:
        Dict[str, Any]: 合并后的新配置字典
    """
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载并合并配置项。如果提供了 YAML 路径，则读取并深度合并，否则直接返回默认配置。

    Args:
        path (Optional[str]): 外部 YAML 配置文件的路径

    Returns:
        Dict[str, Any]: 最终生效的合并配置字典

    Raises:
        RuntimeError: 当缺少 PyYAML 库时抛出
        ValueError: 当配置文件非字典结构时抛出
    """
    config = deepcopy(DEFAULT_CONFIG)
    if not path:
        return config

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required when --config is used. Install simulator/requirements.txt") from exc

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fp:
        loaded = yaml.safe_load(fp) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"config file must contain a YAML mapping: {path}")
    return deep_merge(config, loaded)
