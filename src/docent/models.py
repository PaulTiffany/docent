from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

Authority = Literal["primary", "official", "contextual", "commentary"]
Confidence = Literal["authoritative", "high", "medium", "low", "unknown"]
AnswerPolicy = Literal["public", "restricted", "refuse-extraction"]


class PublicLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    url: HttpUrl


class SourceLocator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    section: str | None = None
    page: int | None = Field(default=None, ge=1)
    url: HttpUrl | None = None
    authority: Authority


class DocentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    record_type: str
    subject_id: str
    title: str
    content: str
    question_forms: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    source: SourceLocator
    speech_act: str | None = None
    boundaries: list[str] = Field(default_factory=list)
    answer_policy: AnswerPolicy = "public"
    public_links: list[PublicLink] = Field(default_factory=list)
    confidence: Confidence = "unknown"
    valid_from: date | None = None
    valid_until: date | None = None
    version: str

    @field_validator("record_id", "record_type", "subject_id", "title", "content", "version")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    def retrieval_text(self) -> str:
        return "\n".join(
            [
                self.title,
                self.content,
                " ".join(self.question_forms),
                " ".join(self.topics),
                " ".join(self.entities),
                " ".join(self.boundaries),
            ]
        )


class RetrievedRecord(BaseModel):
    record: DocentRecord
    score: float = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["human", "docent"]
    content: str


class InferenceMode(str, Enum):
    live = "live"
    deterministic = "deterministic"


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt_tokens: int | None = Field(default=None, ge=0, le=100_000_000)
    completion_tokens: int | None = Field(default=None, ge=0, le=100_000_000)
    total_tokens: int | None = Field(default=None, ge=0, le=100_000_000)


class ProviderCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_content: str = Field(min_length=1, max_length=100_000)
    configured_model: str = Field(min_length=1, max_length=256)
    actual_model: str | None = Field(default=None, min_length=1, max_length=256)
    provider_request_id: str | None = Field(default=None, min_length=1, max_length=256)
    finish_reason: str | None = Field(default=None, min_length=1, max_length=128)
    usage: TokenUsage | None = None
    response_format_mode: Literal["json_object", "text", "deterministic"]
    duration_ms: int = Field(ge=0, le=3_600_000)


class ProviderProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inference_mode: InferenceMode
    provider: str = Field(min_length=1, max_length=64)
    configured_model: str = Field(min_length=1, max_length=256)
    actual_model: str | None = Field(default=None, min_length=1, max_length=256)
    provider_request_id: str | None = Field(default=None, min_length=1, max_length=256)
    finish_reason: str | None = Field(default=None, min_length=1, max_length=128)
    usage: TokenUsage | None = None
    response_format_mode: Literal["json_object", "text", "deterministic"]
    duration_ms: int = Field(ge=0, le=3_600_000)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=12000)
    mode: InferenceMode | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=12000)
    limit: int | None = Field(default=None, ge=1, le=20)


class SearchHit(BaseModel):
    record_id: str
    title: str
    score: float
    authority: Authority
    reasons: list[str]


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class DocentEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str = Field(min_length=1, max_length=12000)
    record_ids: list[str] = Field(default_factory=list)
    grounded: bool
    limitations: list[str] = Field(default_factory=list)


class ChatResponse(DocentEnvelope):
    session_id: str
    retrieval: list[SearchHit] = Field(default_factory=list)
    provenance: ProviderProvenance


class PublicConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    role: str
    description: str
    default_inference_mode: InferenceMode
    live_inference_enabled: bool
    deterministic_mode_enabled: bool
    enabled_inference_modes: list[InferenceMode]
    provider: str
    configured_model: str
    app_title: str | None = None
    live_daily_budget_enabled: bool
    live_daily_budget_remaining: int | None = Field(default=None, ge=0)


class AgentConnectionState(str, Enum):
    disconnected = "disconnected"
    connecting = "connecting"
    ready = "ready"
    busy = "busy"
    degraded = "degraded"


class RoomMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=1)
    room_epoch: str = Field(min_length=1, max_length=128)
    sender_id: str = Field(min_length=1, max_length=128)
    sender_role: Literal["human", "agent", "system"]
    text: str = Field(min_length=1, max_length=12000)
    timestamp: datetime
    directed_recipient: str | None = Field(default=None, min_length=1, max_length=128)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)


class RoomState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_epoch: str
    latest_sequence: int = Field(ge=0)
    agent_connection_state: AgentConnectionState
    agent_busy: bool
    queued_turn_count: int = Field(ge=0)


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    triggering_message: RoomMessage
    recent_context: list[RoomMessage]
    retrieved_records: list[RetrievedRecord]
    session_id: str = Field(min_length=1, max_length=128)
    room_metadata: dict[str, str] = Field(default_factory=dict)


class TurnResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: DocentEnvelope
    source_record_ids: list[str] = Field(default_factory=list)
    status: Literal["completed", "refused", "failed"]
    started_at: datetime
    completed_at: datetime
    duration_ms: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoomMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sender_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=12000)
    session_id: str = Field(min_length=1, max_length=128)
    directed_recipient: str | None = Field(default=None, min_length=1, max_length=128)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)


class RoomMessageCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: RoomMessage
    duplicate: bool
    queued: bool
    state: RoomState


class RoomMessagesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[RoomMessage]
    state: RoomState


class RoomResetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    previous_epoch: str
    state: RoomState
