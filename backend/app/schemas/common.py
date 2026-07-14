"""
common.py —— API 标准统一响应架构的 Schema 协议包装器

本模块负责将后端所有 API 端点返回的数据，统一格式化为前端 Arco Design 标准解析结构。
格式标准：
  - 含有业务层错误码 code
  - 含有交互提示信息 message
  - 含有具体实体数据 data
  - 为防脏数据或数据库熔断降级，若数据携带源状态 (data_source 等)，自动包装降级状态 (fallback 等)
  - 自动为每次调用请求生成唯一的 request_id，用作分布式日志追踪和问题排查
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4


def ok(data: Any, message: str = "success") -> Dict[str, Any]:
    """
    将原生数据包裹进标准的统一 JSON 协议响应结构体中。

    Args:
        data (Any): 原生业务数据。
                    如果是个字典且包含 'data_source' 等字段，则会展开为带指标降级感知字段的结构。
        message (str): 交互提示词。默认为 "success"。

    Returns:
        Dict[str, Any]: 符合 API 标准协议的字典格式数据
    """
    # 如果数据带有备用降级特征（来自 StatisticsService 等服务），解包并透出数据源和降级细节
    if isinstance(data, dict) and "data_source" in data and "data" in data:
        return {
            "code": 0,
            "message": message,
            "data": data["data"],
            "data_source": data["data_source"],
            "fallback": data["fallback"],
            "reason": data["reason"],
            "request_id": f"req_{uuid4().hex[:12]}",
        }
    
    # 正常返回包裹
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": f"req_{uuid4().hex[:12]}",
    }
