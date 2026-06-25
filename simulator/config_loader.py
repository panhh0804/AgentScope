from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional


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
        "scenario_weights": {
            "success": 70,
            "agent_failed": 10,
            "tool_failed": 5,
            "high_latency": 5,
            "retry": 5,
            "token_overuse": 3,
            "loop": 2,
        },
        "latency_ms": {
            "normal_min": 300,
            "normal_max": 4500,
            "high_min": 10000,
            "high_max": 30000,
            "tool_min": 100,
            "tool_max": 2500,
        },
        "tokens": {
            "prompt_min": 200,
            "prompt_max": 2500,
            "completion_min": 200,
            "completion_max": 1800,
            "overuse_prompt_min": 12000,
            "overuse_prompt_max": 18000,
            "overuse_completion_min": 8000,
            "overuse_completion_max": 12000,
        },
        "timing": {
            "gap_min_ms": 50,
            "gap_max_ms": 500,
        },
    },
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
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

