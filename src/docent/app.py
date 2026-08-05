from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from docent.config import get_settings, load_contract
from docent.corpus import load_records
from docent.development import (
    CapabilityRecord,
    DecisionRecord,
    DevelopmentFrontier,
    ExperimentRecord,
    PathwayRecord,
    derive_development_frontier,
    load_development_manifest,
)
from docent.development_records import development_records
from docent.history import SessionHistory
from docent.models import (
    ChatRequest,
    ChatResponse,
    InferenceMode,
    PublicConfig,
    RoomMessageCreate,
    RoomMessageCreateResponse,
    RoomMessagesResponse,
    RoomResetResponse,
    RoomState,
    SearchRequest,
    SearchResponse,
)
from docent.providers import build_provider
from docent.providers.errors import (
    InferenceModeDisabledError,
    LiveBudgetExhaustedError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
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
development_manifest = load_development_manifest(settings.development_root)
development_frontier = derive_development_frontier(development_manifest)
records = load_records(settings.corpus_path) + development_records(development_manifest)
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


@app.get("/api/config/public", response_model=PublicConfig)
async def public_config() -> PublicConfig:
    modes = [InferenceMode.live] if settings.live_inference_enabled else []
    if settings.allow_deterministic_mode:
        modes.append(InferenceMode.deterministic)
    return PublicConfig(
        name=contract.identity.name,
        role=contract.identity.role,
        description=settings.description,
        default_inference_mode=InferenceMode(settings.default_inference_mode),
        live_inference_enabled=settings.live_inference_enabled,
        deterministic_mode_enabled=settings.allow_deterministic_mode,
        enabled_inference_modes=modes,
        provider=settings.provider,
        configured_model=settings.model
        if settings.live_inference_enabled
        else "deterministic-corpus",
        app_title=settings.app_title,
        live_daily_budget_enabled=service.live_budget.enabled,
        live_daily_budget_remaining=await service.live_budget.remaining(),
    )


@app.get("/api/development/capabilities", response_model=list[CapabilityRecord])
async def development_capabilities() -> list[CapabilityRecord]:
    return sorted(development_manifest.capabilities, key=lambda item: item.capability_id)


@app.get("/api/development/capabilities/{capability_id}", response_model=CapabilityRecord)
async def development_capability(capability_id: str) -> CapabilityRecord:
    for capability in development_manifest.capabilities:
        if capability.capability_id == capability_id:
            return capability
    raise HTTPException(
        status_code=404,
        detail={"code": "capability_not_found", "message": "Unknown capability ID."},
    )


@app.get("/api/development/pathways", response_model=list[PathwayRecord])
async def development_pathways() -> list[PathwayRecord]:
    return sorted(development_manifest.pathways, key=lambda item: item.pathway_id)


@app.get("/api/development/pathways/{pathway_id}", response_model=PathwayRecord)
async def development_pathway(pathway_id: str) -> PathwayRecord:
    for pathway in development_manifest.pathways:
        if pathway.pathway_id == pathway_id:
            return pathway
    raise HTTPException(
        status_code=404,
        detail={"code": "pathway_not_found", "message": "Unknown pathway ID."},
    )


@app.get("/api/development/frontier", response_model=DevelopmentFrontier)
async def development_state_frontier() -> DevelopmentFrontier:
    return development_frontier


@app.get("/api/development/decisions", response_model=list[DecisionRecord])
async def development_decisions() -> list[DecisionRecord]:
    return sorted(development_manifest.decisions, key=lambda item: item.decision_id)


@app.get("/api/development/experiments", response_model=list[ExperimentRecord])
async def development_experiments() -> list[ExperimentRecord]:
    return sorted(development_manifest.experiments, key=lambda item: item.experiment_id)


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(hits=service.search(request.query, request.limit))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    client_key = http_request.client.host if http_request.client else "unknown"
    if not await rate_limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    try:
        return await service.answer(request.session_id, request.message, request.mode)
    except InferenceModeDisabledError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": exc.public_code, "message": exc.public_message},
        ) from exc
    except LiveBudgetExhaustedError as exc:
        raise HTTPException(
            status_code=429,
            detail={"code": exc.public_code, "message": exc.public_message},
        ) from exc
    except ProviderError as exc:
        logger.warning("Live provider request failed: %s", exc.public_code)
        status_code = 504 if isinstance(exc, ProviderTimeoutError) else 503
        if isinstance(exc, ProviderRateLimitError):
            status_code = 429
        detail = {"code": exc.public_code, "message": exc.public_message}
        if exc.retry_after is not None:
            detail["retry_after_seconds"] = exc.retry_after
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except Exception as exc:
        logger.exception("Docent turn failed")
        raise HTTPException(
            status_code=503,
            detail={
                "code": "live_inference_unavailable",
                "message": "Docent is temporarily unavailable.",
            },
        ) from exc


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


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
