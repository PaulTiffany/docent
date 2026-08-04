from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOCENT_", extra="ignore")

    name: str = "Example Docent"
    description: str = "A bounded guide to the configured collection."
    provider: str = "mock"
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    corpus_path: Path = Path("corpus/records.jsonl")
    contract_path: Path = Path("config/docent.yaml")
    history_limit: int = Field(default=5, ge=0, le=20)
    retrieval_limit: int = Field(default=6, ge=1, le=20)
    min_retrieval_score: float = Field(default=0.05, ge=0)
    max_output_tokens: int = Field(default=700, ge=50, le=8000)
    temperature: float = Field(default=0.2, ge=0, le=2)
    request_timeout_seconds: float = Field(default=45, gt=0, le=300)
    rate_limit_per_hour: int = Field(default=120, ge=1, le=100000)
    allowed_origins: str = "http://localhost:7860"
    log_level: str = "INFO"
    environment: str = "development"
    room_history_limit: int = Field(default=100, ge=1, le=10000)
    room_context_limit: int = Field(default=12, ge=0, le=100)
    room_queue_limit: int = Field(default=20, ge=1, le=1000)
    room_reset_enabled: bool = True

    @property
    def allow_room_reset(self) -> bool:
        return self.room_reset_enabled and self.environment.casefold() in {"development", "test"}

    @property
    def origins(self) -> list[str]:
        return [part.strip() for part in self.allowed_origins.split(",") if part.strip()]


class IdentityContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: str
    non_impersonation: str


class JurisdictionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: list[str]
    forbidden: list[str]


class SourcePolicyContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: list[str]
    rules: list[str]


class BehaviorContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_once: bool = True
    concise_by_default: bool = True
    admit_absence: bool = True
    no_unsolicited_monologue: bool = True
    style: str


class RefusalContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unsupported: str
    extraction: str


class DocentContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity: IdentityContract
    jurisdiction: JurisdictionContract
    source_policy: SourcePolicyContract
    behavior: BehaviorContract
    refusal: RefusalContract


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def load_contract(path: Path) -> DocentContract:
    with path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle)
    return DocentContract.model_validate(raw)
