import pytest
from fastapi.testclient import TestClient

from docent.app import app
from docent.models import AgentConnectionState, RoomMessageCreate
from docent.room import (
    InMemoryRoomStore,
    InMemoryTurnQueue,
    SharedRoomService,
    StaleRoomCursorError,
    TurnQueueFullError,
)


def build_room(*, history: int = 10, queue: int = 10, context: int = 3) -> SharedRoomService:
    return SharedRoomService(
        store=InMemoryRoomStore(history),
        queue=InMemoryTurnQueue(queue),
        recent_context_limit=context,
    )


def request(index: int, **overrides: str) -> RoomMessageCreate:
    values = {
        "sender_id": "visitor",
        "text": f"Message {index}",
        "session_id": "session",
        "idempotency_key": f"key-{index}",
    }
    values.update(overrides)
    return RoomMessageCreate(**values)


@pytest.mark.asyncio
async def test_sequences_and_cursor_retrieval_are_monotonic() -> None:
    room = build_room()
    first = await room.append_human(request(1))
    second = await room.append_human(request(2))
    assert [first.message.sequence, second.message.sequence] == [1, 2]
    result = await room.messages(first.message.sequence, first.message.room_epoch)
    assert [message.message_id for message in result.messages] == [second.message.message_id]


@pytest.mark.asyncio
async def test_bounded_history_truncates_oldest_messages() -> None:
    room = build_room(history=2)
    for index in range(3):
        await room.append_human(request(index))
    result = await room.messages(0, None)
    assert [message.sequence for message in result.messages] == [2, 3]


@pytest.mark.asyncio
async def test_reset_increments_epoch_and_rejects_stale_epoch() -> None:
    room = build_room()
    created = await room.append_human(request(1))
    reset = await room.reset()
    assert int(reset.state.room_epoch) == int(reset.previous_epoch) + 1
    with pytest.raises(StaleRoomCursorError):
        await room.messages(created.message.sequence, created.message.room_epoch)


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_does_not_insert_or_enqueue_twice() -> None:
    room = build_room()
    first = await room.append_human(request(1))
    duplicate = await room.append_human(request(99, idempotency_key="key-1"))
    assert duplicate.duplicate is True
    assert duplicate.queued is False
    assert duplicate.message.message_id == first.message.message_id
    assert duplicate.state.latest_sequence == 1
    assert duplicate.state.queued_turn_count == 1


@pytest.mark.asyncio
async def test_directed_recipient_is_preserved() -> None:
    room = build_room()
    created = await room.append_human(request(1, directed_recipient="guide"))
    assert created.message.directed_recipient == "guide"


@pytest.mark.asyncio
async def test_maximum_queue_is_enforced_without_inserting_message() -> None:
    room = build_room(queue=1)
    await room.append_human(request(1))
    with pytest.raises(TurnQueueFullError):
        await room.append_human(request(2))
    assert (await room.status()).latest_sequence == 1


@pytest.mark.asyncio
async def test_room_status_transitions() -> None:
    room = build_room()
    assert (await room.status()).agent_connection_state is AgentConnectionState.disconnected
    await room.set_connection_state(AgentConnectionState.ready)
    assert (await room.status()).agent_busy is False
    await room.set_connection_state(AgentConnectionState.busy)
    assert (await room.status()).agent_busy is True


def test_http_room_contract_and_stale_cursor() -> None:
    client = TestClient(app)
    client.post("/api/room/reset")
    created = client.post(
        "/api/room/messages",
        json={
            "sender_id": "visitor",
            "text": "Hello",
            "session_id": "web",
            "directed_recipient": "guide",
            "idempotency_key": "http-key",
        },
    )
    assert created.status_code == 201
    body = created.json()
    duplicate = client.post(
        "/api/room/messages",
        json={
            "sender_id": "visitor",
            "text": "Changed",
            "session_id": "web",
            "idempotency_key": "http-key",
        },
    )
    assert duplicate.json()["duplicate"] is True
    old_epoch = body["message"]["room_epoch"]
    client.post("/api/room/reset")
    stale = client.get("/api/room/messages", params={"after": 1, "epoch": old_epoch})
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_room_epoch"


def test_malformed_or_internal_room_fields_are_rejected() -> None:
    client = TestClient(app)
    malformed = client.post(
        "/api/room/messages", json={"sender_id": "", "text": "", "session_id": "web"}
    )
    assert malformed.status_code == 422
    internal = client.post(
        "/api/room/messages",
        json={
            "sender_id": "visitor",
            "text": "Hello",
            "session_id": "web",
            "retrieved_records": [{"content": "internal"}],
        },
    )
    assert internal.status_code == 422


def test_current_chat_http_behavior_remains_available() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/chat", json={"session_id": "compatibility", "message": "What can this docent answer?"}
    )
    assert response.status_code == 200
    assert response.json()["session_id"] == "compatibility"
