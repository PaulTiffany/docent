from __future__ import annotations

import asyncio
from collections import deque
from datetime import UTC, datetime
from uuid import uuid4

from docent.contracts import RoomStore, TurnQueue
from docent.models import (
    AgentConnectionState,
    RoomMessage,
    RoomMessageCreate,
    RoomMessageCreateResponse,
    RoomMessagesResponse,
    RoomResetResponse,
    RoomState,
    TurnRequest,
)


class StaleRoomCursorError(ValueError):
    def __init__(self, current_epoch: str) -> None:
        self.current_epoch = current_epoch
        super().__init__("The cursor belongs to an earlier room epoch.")


class CursorEpochRequiredError(ValueError):
    pass


class TurnQueueFullError(RuntimeError):
    pass


class InMemoryRoomStore:
    def __init__(self, maximum_history: int) -> None:
        if maximum_history < 1:
            raise ValueError("maximum_history must be at least 1")
        self.maximum_history = maximum_history
        self._epoch_number = 1
        self._sequence = 0
        self._messages: deque[RoomMessage] = deque(maxlen=maximum_history)
        self._idempotency: dict[str, RoomMessage] = {}
        self._connection_state = AgentConnectionState.disconnected
        self._lock = asyncio.Lock()

    @property
    def epoch(self) -> str:
        return str(self._epoch_number)

    async def append(
        self,
        *,
        sender_id: str,
        sender_role: str,
        text: str,
        directed_recipient: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[RoomMessage, bool]:
        async with self._lock:
            if idempotency_key and idempotency_key in self._idempotency:
                return self._idempotency[idempotency_key], True
            self._sequence += 1
            message = RoomMessage(
                message_id=uuid4().hex,
                sequence=self._sequence,
                room_epoch=self.epoch,
                sender_id=sender_id,
                sender_role=sender_role,
                text=text,
                timestamp=datetime.now(UTC),
                directed_recipient=directed_recipient,
                idempotency_key=idempotency_key,
            )
            self._messages.append(message)
            if idempotency_key:
                self._idempotency[idempotency_key] = message
            return message, False

    async def get_by_idempotency_key(self, key: str) -> RoomMessage | None:
        async with self._lock:
            return self._idempotency.get(key)

    async def messages_after(self, cursor: int, epoch: str | None) -> list[RoomMessage]:
        async with self._lock:
            if cursor > 0 and epoch is None:
                raise CursorEpochRequiredError("epoch is required when after is greater than zero")
            if epoch is not None and epoch != self.epoch:
                raise StaleRoomCursorError(self.epoch)
            return [message for message in self._messages if message.sequence > cursor]

    async def recent(self, limit: int) -> list[RoomMessage]:
        if limit < 0:
            raise ValueError("limit cannot be negative")
        async with self._lock:
            return [] if limit == 0 else list(self._messages)[-limit:]

    async def state(self, queued_turn_count: int) -> RoomState:
        async with self._lock:
            return RoomState(
                room_epoch=self.epoch,
                latest_sequence=self._sequence,
                agent_connection_state=self._connection_state,
                agent_busy=self._connection_state is AgentConnectionState.busy,
                queued_turn_count=queued_turn_count,
            )

    async def set_connection_state(self, state: AgentConnectionState) -> None:
        async with self._lock:
            self._connection_state = state

    async def reset(self) -> str:
        async with self._lock:
            previous = self.epoch
            self._epoch_number += 1
            self._sequence = 0
            self._messages.clear()
            self._idempotency.clear()
            self._connection_state = AgentConnectionState.disconnected
            return previous


class InMemoryTurnQueue:
    def __init__(self, maximum_size: int) -> None:
        if maximum_size < 1:
            raise ValueError("maximum_size must be at least 1")
        self._maximum_size = maximum_size
        self._items: deque[TurnRequest] = deque()
        self._lock = asyncio.Lock()

    @property
    def maximum_size(self) -> int:
        return self._maximum_size

    async def enqueue(self, request: TurnRequest) -> bool:
        async with self._lock:
            if len(self._items) >= self.maximum_size:
                return False
            self._items.append(request)
            return True

    async def dequeue(self) -> TurnRequest | None:
        async with self._lock:
            return self._items.popleft() if self._items else None

    async def size(self) -> int:
        async with self._lock:
            return len(self._items)

    async def clear(self) -> None:
        async with self._lock:
            self._items.clear()


class SharedRoomService:
    def __init__(self, *, store: RoomStore, queue: TurnQueue, recent_context_limit: int) -> None:
        self.store = store
        self.queue = queue
        self.recent_context_limit = recent_context_limit
        self._lock = asyncio.Lock()

    async def append_human(self, request: RoomMessageCreate) -> RoomMessageCreateResponse:
        async with self._lock:
            if request.idempotency_key:
                existing = await self.store.get_by_idempotency_key(request.idempotency_key)
                if existing:
                    return RoomMessageCreateResponse(
                        message=existing,
                        duplicate=True,
                        queued=False,
                        state=await self.status(),
                    )
            if await self.queue.size() >= self.queue.maximum_size:
                raise TurnQueueFullError("The room turn queue is full.")
            recent = await self.store.recent(self.recent_context_limit)
            message, duplicate = await self.store.append(
                sender_id=request.sender_id,
                sender_role="human",
                text=request.text,
                directed_recipient=request.directed_recipient,
                idempotency_key=request.idempotency_key,
            )
            turn = TurnRequest(
                triggering_message=message,
                recent_context=recent,
                retrieved_records=[],
                session_id=request.session_id,
                room_metadata={"room_epoch": message.room_epoch},
            )
            queued = await self.queue.enqueue(turn)
            return RoomMessageCreateResponse(
                message=message, duplicate=duplicate, queued=queued, state=await self.status()
            )

    async def messages(self, cursor: int, epoch: str | None) -> RoomMessagesResponse:
        return RoomMessagesResponse(
            messages=await self.store.messages_after(cursor, epoch), state=await self.status()
        )

    async def status(self) -> RoomState:
        return await self.store.state(await self.queue.size())

    async def reset(self) -> RoomResetResponse:
        async with self._lock:
            previous = await self.store.reset()
            await self.queue.clear()
            return RoomResetResponse(previous_epoch=previous, state=await self.status())

    async def set_connection_state(self, state: AgentConnectionState) -> None:
        setter = getattr(self.store, "set_connection_state", None)
        if setter is None:
            raise RuntimeError("The configured room store cannot update connection state")
        await setter(state)
