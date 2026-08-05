from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from docent.config import DocentContract, Settings
from docent.history import SessionHistory
from docent.live_budget import InMemoryDailyBudget
from docent.models import (
    ChatMessage,
    ChatResponse,
    DocentEnvelope,
    InferenceMode,
    ProviderCompletion,
    ProviderProvenance,
    SearchHit,
)
from docent.prompting import build_system_prompt, build_user_prompt
from docent.providers.base import ModelProvider
from docent.providers.errors import (
    InferenceModeDisabledError,
    LiveBudgetExhaustedError,
    ModelEnvelopeError,
)
from docent.providers.mock import MockProvider
from docent.retrieval import LexicalRetriever

logger = logging.getLogger(__name__)


class DocentService:
    def __init__(
        self,
        *,
        settings: Settings,
        contract: DocentContract,
        retriever: LexicalRetriever,
        provider: ModelProvider,
        history: SessionHistory,
        deterministic_provider: ModelProvider | None = None,
        live_budget: InMemoryDailyBudget | None = None,
    ) -> None:
        self.settings = settings
        self.contract = contract
        self.retriever = retriever
        self.provider = provider
        self.deterministic_provider = deterministic_provider or MockProvider()
        self.history = history
        self.live_budget = live_budget or InMemoryDailyBudget(settings.live_daily_budget)
        self.system_prompt = build_system_prompt(contract)

    def search(self, query: str, limit: int | None = None) -> list[SearchHit]:
        retrieved = self.retriever.search(
            query,
            limit=limit or self.settings.retrieval_limit,
            minimum_score=self.settings.min_retrieval_score,
        )
        return [
            SearchHit(
                record_id=item.record.record_id,
                title=item.record.title,
                score=round(item.score, 6),
                authority=item.record.source.authority,
                reasons=item.reasons,
            )
            for item in retrieved
        ]

    def resolve_mode(self, requested: InferenceMode | None) -> InferenceMode:
        mode = requested or InferenceMode(self.settings.default_inference_mode)
        if mode is InferenceMode.live and not self.settings.live_inference_enabled:
            raise InferenceModeDisabledError("live inference is not configured")
        if mode is InferenceMode.deterministic and not self.settings.allow_deterministic_mode:
            raise InferenceModeDisabledError("deterministic inference is disabled")
        return mode

    async def answer(
        self, session_id: str, message: str, mode: InferenceMode | None = None
    ) -> ChatResponse:
        selected_mode = self.resolve_mode(mode)
        history = await self.history.get(session_id)
        retrieved = self.retriever.search(
            message,
            limit=self.settings.retrieval_limit,
            minimum_score=self.settings.min_retrieval_score,
        )
        user_prompt = build_user_prompt(message, history, retrieved)

        selected_provider = self.provider
        if selected_mode is InferenceMode.deterministic:
            selected_provider = self.deterministic_provider
        else:
            if not await self.live_budget.reserve():
                raise LiveBudgetExhaustedError("daily live inference budget exhausted")

        completion = await selected_provider.complete(
            system_prompt=self.system_prompt, user_prompt=user_prompt
        )
        envelope = self._parse_envelope(
            completion, allowed_record_ids={r.record.record_id for r in retrieved}
        )

        await self.history.append(session_id, ChatMessage(role="human", content=message))
        await self.history.append(session_id, ChatMessage(role="docent", content=envelope.reply))

        retrieval = [
            SearchHit(
                record_id=item.record.record_id,
                title=item.record.title,
                score=round(item.score, 6),
                authority=item.record.source.authority,
                reasons=item.reasons,
            )
            for item in retrieved
        ]
        provenance = ProviderProvenance(
            inference_mode=selected_mode,
            provider=selected_provider.provider_label,
            configured_model=completion.configured_model,
            actual_model=completion.actual_model,
            provider_request_id=completion.provider_request_id,
            finish_reason=completion.finish_reason,
            usage=completion.usage,
            response_format_mode=completion.response_format_mode,
            duration_ms=completion.duration_ms,
        )
        return ChatResponse(
            session_id=session_id,
            retrieval=retrieval,
            provenance=provenance,
            **envelope.model_dump(),
        )

    def _parse_envelope(
        self, completion: ProviderCompletion, allowed_record_ids: set[str]
    ) -> DocentEnvelope:
        candidate = completion.raw_content.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
        try:
            payload = json.loads(candidate)
            envelope = DocentEnvelope.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Invalid provider envelope")
            raise ModelEnvelopeError("invalid model envelope") from exc

        invalid_ids = [
            record_id for record_id in envelope.record_ids if record_id not in allowed_record_ids
        ]
        valid_ids = list(
            dict.fromkeys(
                record_id for record_id in envelope.record_ids if record_id in allowed_record_ids
            )
        )
        if invalid_ids:
            logger.warning("Provider used unavailable record IDs")
            envelope.limitations.append("One or more unsupported source identifiers were removed.")
        envelope.record_ids = valid_ids
        if not envelope.record_ids:
            envelope.grounded = False
        return envelope
