from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from docent.config import get_settings, load_contract
from docent.corpus import load_records
from docent.history import SessionHistory
from docent.models import ChatRequest, ChatResponse, SearchRequest, SearchResponse
from docent.providers import build_provider
from docent.rate_limit import InMemoryRateLimiter
from docent.retrieval import LexicalRetriever
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
    settings=settings,
    contract=contract,
    retriever=retriever,
    provider=provider,
    history=history,
)
rate_limiter = InMemoryRateLimiter(settings.rate_limit_per_hour)

app = FastAPI(title="Docent", version="0.1.0")
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


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
