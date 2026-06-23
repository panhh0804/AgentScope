from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4


def ok(data: Any, message: str = "success") -> Dict[str, Any]:
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": f"req_{uuid4().hex[:12]}",
    }

