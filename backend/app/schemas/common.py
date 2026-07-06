from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4


def ok(data: Any, message: str = "success") -> Dict[str, Any]:
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
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": f"req_{uuid4().hex[:12]}",
    }

