from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from app.services import mock_data


class RealtimeService:
    def __init__(self) -> None:
        self._redis = None

    def _client(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis

            self._redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "middleware"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
            )
            self._redis.ping()
        except Exception:
            self._redis = False
        return self._redis

    def _get_json(self, key: str) -> Optional[Any]:
        client = self._client()
        if not client:
            return None
        value = client.get(key)
        if not value:
            return None
        return json.loads(value)

    def overview(self) -> Dict:
        return self._get_json("agentscope:realtime:overview") or mock_data.realtime_overview()

    def trend(self, minutes: int) -> List[Dict]:
        data = self._get_json("agentscope:realtime:trend")
        return data[-minutes:] if data else mock_data.realtime_trend(minutes)

    def agents(self) -> List[Dict]:
        return self._get_json("agentscope:realtime:agents") or mock_data.realtime_agents()

    def alerts(self) -> List[Dict]:
        return self._get_json("agentscope:realtime:alerts") or mock_data.recent_alerts()

