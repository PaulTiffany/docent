import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import docent.app as app_module
from docent.config import Settings, load_contract
from docent.history import SessionHistory
from docent.models import DocentRecord, ProviderCompletion, SourceLocator
from docent.retrieval import LexicalRetriever
from docent.service import DocentService


def record(record_id: str, policy: str, content: str) -> DocentRecord:
    return DocentRecord(
        record_id=record_id,
        record_type="test",
        subject_id="boundary-test",
        title=f"Title {record_id}",
        content=content,
        question_forms=[content],
        topics=["boundary"],
        entities=[],
        source=SourceLocator(document_id="test", section="public boundary", authority="primary"),
        answer_policy=policy,
        confidence="authoritative",
        version="1",
    )


class CapturingProvider:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.user_prompt = ""

    provider_label = "test"
    configured_model = "test-model"

    async def complete(self, *, system_prompt: str, user_prompt: str) -> ProviderCompletion:
        self.user_prompt = user_prompt
        return ProviderCompletion(
            raw_content=json.dumps(self.payload),
            configured_model=self.configured_model,
            response_format_mode="json_object",
            duration_ms=0,
        )


def test_public_retrieval_excludes_highly_relevant_non_public_records() -> None:
    retriever = LexicalRetriever(
        [
            record("public-safe", "public", "ordinary public overview"),
            record("restricted-secret", "restricted", "ultraviolet banana exact phrase"),
            record("refuse-secret", "refuse-extraction", "ultraviolet banana exact phrase"),
        ]
    )

    public_hits = retriever.search("ultraviolet banana exact phrase", limit=10)
    internal_hits = retriever.search_internal("ultraviolet banana exact phrase", limit=10)

    assert all(hit.record.answer_policy == "public" for hit in public_hits)
    assert {hit.record.record_id for hit in internal_hits} >= {
        "restricted-secret",
        "refuse-secret",
    }


@pytest.mark.asyncio
async def test_restricted_records_never_enter_prompt_or_response() -> None:
    provider = CapturingProvider(
        {
            "reply": "A bounded answer.",
            "record_ids": ["restricted-secret", "public-safe", "public-safe"],
            "grounded": True,
            "limitations": [],
        }
    )
    settings = Settings(provider="mock")
    service = DocentService(
        settings=settings,
        contract=load_contract(Path("config/docent.yaml")),
        retriever=LexicalRetriever(
            [
                record("public-safe", "public", "ultraviolet banana public summary"),
                record("restricted-secret", "restricted", "ultraviolet banana restricted detail"),
            ]
        ),
        provider=provider,
        history=SessionHistory(settings.history_limit),
    )

    response = await service.answer("boundary", "ultraviolet banana")

    assert "restricted detail" not in provider.user_prompt
    assert "restricted-secret" not in provider.user_prompt
    assert response.record_ids == ["public-safe"]
    assert response.grounded is True


def test_search_endpoint_does_not_expose_non_public_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe = record("public-safe", "public", "ultraviolet banana public summary")
    restricted = record(
        "restricted-secret", "restricted", "ultraviolet banana restricted title and content"
    )
    monkeypatch.setattr(app_module.service, "retriever", LexicalRetriever([safe, restricted]))

    response = TestClient(app_module.app).post(
        "/api/search", json={"query": "ultraviolet banana", "limit": 20}
    )

    assert response.status_code == 200
    serialized = response.text
    assert "restricted-secret" not in serialized
    assert "restricted title" not in serialized
    assert all(hit["record_id"] == "public-safe" for hit in response.json()["hits"])


def test_grounding_is_cleared_when_provider_sources_are_invalid() -> None:
    settings = Settings(provider="mock")
    service = DocentService(
        settings=settings,
        contract=load_contract(Path("config/docent.yaml")),
        retriever=LexicalRetriever([record("public-safe", "public", "safe")]),
        provider=CapturingProvider({}),
        history=SessionHistory(settings.history_limit),
    )

    envelope = service._parse_envelope(
        ProviderCompletion(
            raw_content=json.dumps(
                {
                    "reply": "Unsupported claim",
                    "record_ids": ["invented", "invented"],
                    "grounded": True,
                    "limitations": [],
                }
            ),
            configured_model="test-model",
            response_format_mode="json_object",
            duration_ms=0,
        ),
        allowed_record_ids={"public-safe"},
    )

    assert envelope.record_ids == []
    assert envelope.grounded is False
