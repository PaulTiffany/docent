from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, date, datetime


class InMemoryDailyBudget:
    """Process-local UTC-day attempt budget; reservations are never refunded."""

    def __init__(
        self,
        limit: int,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.limit = limit
        self._now = now or (lambda: datetime.now(UTC))
        self._day: date | None = None
        self._used = 0
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    async def reserve(self) -> bool:
        async with self._lock:
            self._roll_day()
            if not self.enabled:
                return True
            if self._used >= self.limit:
                return False
            self._used += 1
            return True

    async def remaining(self) -> int | None:
        async with self._lock:
            self._roll_day()
            return max(self.limit - self._used, 0) if self.enabled else None

    def _roll_day(self) -> None:
        current_day = self._now().astimezone(UTC).date()
        if current_day != self._day:
            self._day = current_day
            self._used = 0
