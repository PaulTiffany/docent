from __future__ import annotations

from datetime import date
from typing import Literal

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


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=12000)


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
