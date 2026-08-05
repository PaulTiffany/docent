from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from docent.config import DocentContract, Settings
from docent.history import SessionHistory
from docent.models import (
    ChatMessage,
    ChatResponse,
    DocentEnvelope,
    SearchHit,
)
from docent.prompting import build_system_prompt, build_user_prompt
from docent.providers.base import ModelProvider
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
    ) -> None:
        self.settings = settings
        self.contract = contract
        self.retriever = retriever
        self.provider = provider
        self.history = history
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

    async def answer(self, session_id: str, message: str) -> ChatResponse:
        history = await self.history.get(session_id)
        retrieved = self.retriever.search(
            message,
            limit=self.settings.retrieval_limit,
            minimum_score=self.settings.min_retrieval_score,
        )
        user_prompt = build_user_prompt(message, history, retrieved)
        raw = await self.provider.complete(
            system_prompt=self.system_prompt, user_prompt=user_prompt
        )
        envelope = self._parse_envelope(
            raw, allowed_record_ids={r.record.record_id for r in retrieved}
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
        return ChatResponse(session_id=session_id, retrieval=retrieval, **envelope.model_dump())

    def _parse_envelope(self, raw: str, allowed_record_ids: set[str]) -> DocentEnvelope:
        candidate = raw.strip()
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
        try:
            payload = json.loads(candidate)
            envelope = DocentEnvelope.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Invalid provider envelope: %s", exc)
            return DocentEnvelope(
                reply=self.contract.refusal.unsupported,
                record_ids=[],
                grounded=False,
                limitations=["The model provider returned an invalid response envelope."],
            )

        invalid_ids = [
            record_id for record_id in envelope.record_ids if record_id not in allowed_record_ids
        ]
        valid_ids = list(
            dict.fromkeys(
                record_id for record_id in envelope.record_ids if record_id in allowed_record_ids
            )
        )
        if invalid_ids:
            logger.warning("Provider invented or used unavailable record IDs: %s", invalid_ids)
            envelope.limitations.append("One or more unsupported source identifiers were removed.")
        envelope.record_ids = valid_ids
        if not envelope.record_ids:
            envelope.grounded = False
        return envelope
