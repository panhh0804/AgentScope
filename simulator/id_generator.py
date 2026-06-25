from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Optional
from uuid import uuid4


class IdGenerator:
    def __init__(self, deterministic: bool = False) -> None:
        self.deterministic = deterministic
        self._counters: DefaultDict[str, int] = defaultdict(int)

    @classmethod
    def from_seed(cls, seed: Optional[int]) -> "IdGenerator":
        return cls(deterministic=seed is not None)

    def new_id(self, prefix: str) -> str:
        if not self.deterministic:
            return f"{prefix}_{uuid4().hex[:16]}"
        self._counters[prefix] += 1
        return f"{prefix}_{self._counters[prefix]:08d}"

