from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from docent.config import get_settings, load_contract
from docent.corpus import load_records
from docent.history import SessionHistory
from docent.models import (
    ChatRequest,
    ChatResponse,
    RoomMessageCreate,
    RoomMessageCreateResponse,
    RoomMessagesResponse,
    RoomResetResponse,
    RoomState,
    SearchRequest,
    SearchResponse,
)
from docent.providers import build_provider
from docent.rate_limit import InMemoryRateLimiter
from docent.retrieval import LexicalRetriever
from docent.room import (
    CursorEpochRequiredError,
    InMemoryRoomStore,
    InMemoryTurnQueue,
    SharedRoomService,
    StaleRoomCursorError,
    TurnQueueFullError,
)
from docent.service import DocentService

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

contract = load_contract(settings.contract_path)
records = load_records(settings.corpus_path)
retriever = LexicalRetriever(records)
provider = build_provider(settings)
history = SessionHistory(settings.history_limit)
service = DocentService(
    settings=settings, contract=contract, retriever=retriever, provider=provider, history=history
)
rate_limiter = InMemoryRateLimiter(settings.rate_limit_per_hour)
room_service = SharedRoomService(
    store=InMemoryRoomStore(settings.room_history_limit),
    queue=InMemoryTurnQueue(settings.room_queue_limit),
    recent_context_limit=settings.room_context_limit,
)

app = FastAPI(title="Docent", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "provider": settings.provider,
        "record_count": len(records),
        "docent": contract.identity.name,
    }


@app.get("/api/config/public")
async def public_config() -> dict:
    return {
        "name": contract.identity.name,
        "role": contract.identity.role,
        "description": settings.description,
        "provider": settings.provider,
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(hits=service.search(request.query, request.limit))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    client_key = http_request.client.host if http_request.client else "unknown"
    if not await rate_limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    try:
        return await service.answer(request.session_id, request.message)
    except Exception as exc:
        logger.exception("Docent turn failed")
        raise HTTPException(status_code=503, detail="Docent is temporarily unavailable") from exc


@app.delete("/api/sessions/{session_id}")
async def clear_session(session_id: str) -> dict:
    await history.clear(session_id)
    return {"cleared": True, "session_id": session_id}


@app.get("/api/room/messages", response_model=RoomMessagesResponse)
async def room_messages(
    after: int = Query(default=0, ge=0),
    epoch: str | None = Query(default=None, min_length=1, max_length=128),
) -> RoomMessagesResponse:
    try:
        return await room_service.messages(after, epoch)
    except CursorEpochRequiredError as exc:
        raise HTTPException(
            status_code=409, detail={"code": "cursor_epoch_required", "message": str(exc)}
        ) from exc
    except StaleRoomCursorError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "stale_room_epoch",
                "message": str(exc),
                "current_epoch": exc.current_epoch,
            },
        ) from exc


@app.post("/api/room/messages", response_model=RoomMessageCreateResponse, status_code=201)
async def create_room_message(request: RoomMessageCreate) -> RoomMessageCreateResponse:
    try:
        result = await room_service.append_human(request)
    except TurnQueueFullError as exc:
        raise HTTPException(
            status_code=429, detail={"code": "turn_queue_full", "message": str(exc)}
        ) from exc
    return result


@app.get("/api/room/status", response_model=RoomState)
async def room_status() -> RoomState:
    return await room_service.status()


@app.post("/api/room/reset", response_model=RoomResetResponse)
async def reset_room() -> RoomResetResponse:
    if not settings.allow_room_reset:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "room_reset_disabled",
                "message": "Room reset is disabled in this environment.",
            },
        )
    return await room_service.reset()


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
