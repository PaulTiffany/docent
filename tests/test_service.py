from pathlib import Path

import pytest

from docent.config import Settings, load_contract
from docent.corpus import load_records
from docent.history import SessionHistory
from docent.providers.mock import MockProvider
from docent.retrieval import LexicalRetriever
from docent.service import DocentService


@pytest.mark.asyncio
async def test_mock_turn_returns_valid_grounded_envelope() -> None:
    settings = Settings(
        provider="mock",
        corpus_path=Path("corpus/records.jsonl"),
        contract_path=Path("config/docent.yaml"),
    )
    service = DocentService(
        settings=settings,
        contract=load_contract(settings.contract_path),
        retriever=LexicalRetriever(load_records(settings.corpus_path)),
        provider=MockProvider(),
        history=SessionHistory(settings.history_limit),
    )
    response = await service.answer("test", "What can this docent answer?")
    assert response.grounded is True
    assert response.record_ids
    assert response.session_id == "test"
