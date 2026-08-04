from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self, limit_per_hour: int) -> None:
        self.limit = limit_per_hour
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - 3600
        async with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True
