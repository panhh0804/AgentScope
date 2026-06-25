from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from real_agent_sdk.event_model import MODEL_NAME


class SiliconFlowError(RuntimeError):
    pass


class SiliconFlowClient:
    def __init__(
        self,
        model: str = MODEL_NAME,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_tokens: int = 512,
    ) -> None:
        load_local_env()
        self.model = model
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.base_url = (base_url or os.getenv("SILICONFLOW_BASE_URL") or "https://api.siliconflow.cn/v1").rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> Dict:
        if not self.api_key:
            raise SiliconFlowError("SILICONFLOW_API_KEY is not set")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise SiliconFlowError(f"SiliconFlow HTTP {exc.code}: {body}") from exc
        except Exception as exc:
            raise SiliconFlowError(f"SiliconFlow request failed: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise SiliconFlowError(f"unexpected SiliconFlow response: {data}") from exc

        usage = data.get("usage") or {}
        return {
            "content": content,
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "raw": data,
        }


def load_local_env() -> None:
    """Load simple KEY=VALUE pairs from local .env files without overriding real env vars."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parent / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            item = line.strip()
            if not item or item.startswith("#") or "=" not in item:
                continue
            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
