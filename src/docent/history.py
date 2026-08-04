from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from docent.models import ChatMessage


class SessionHistory:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._sessions: dict[str, deque[ChatMessage]] = defaultdict(
            lambda: deque(maxlen=max(1, limit * 2))
        )
        self._lock = asyncio.Lock()

    async def get(self, session_id: str) -> list[ChatMessage]:
        if self.limit == 0:
            return []
        async with self._lock:
            return list(self._sessions[session_id])[-self.limit :]

    async def append(self, session_id: str, message: ChatMessage) -> None:
        if self.limit == 0:
            return
        async with self._lock:
            self._sessions[session_id].append(message)

    async def clear(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)
