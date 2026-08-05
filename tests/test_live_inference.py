import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from docent.config import Settings, load_contract
from docent.history import SessionHistory
from docent.live_budget import InMemoryDailyBudget
from docent.models import DocentRecord, InferenceMode, ProviderCompletion, SourceLocator
from docent.providers.errors import (
    InferenceModeDisabledError,
    LiveBudgetExhaustedError,
    ModelEnvelopeError,
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderMalformedResponseError,
    ProviderModelUnavailableError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from docent.providers.mock import MockProvider
from docent.providers.openai_compatible import OpenAICompatibleProvider
from docent.retrieval import LexicalRetriever
from docent.service import DocentService


def _provider(handler, **kwargs) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        api_key="test-only-key",
        base_url=kwargs.pop("base_url", "https://compatible.example/v1"),
        model=kwargs.pop("model", "openrouter/free"),
        max_output_tokens=200,
        temperature=0.1,
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def _success(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "request-safe",
            "model": "provider/actual-free-model",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "reply": "Bounded synthesis",
                                "record_ids": ["safe", "safe", "invented"],
                                "grounded": True,
                                "limitations": [],
                            }
                        )
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "reasoning": "must not be exposed",
        },
    )


@pytest.mark.asyncio
async def test_openai_compatible_metadata_and_optional_openrouter_headers() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(request.headers)
        return _success(request)

    provider = _provider(
        handler,
        site_url="https://example.test/docent/",
        app_title="Docent",
        base_url="https://openrouter.ai/api/v1",
    )
    completion = await provider.complete(system_prompt="system", user_prompt="user")
    assert provider.provider_label == "openrouter"

    assert completion.configured_model == "openrouter/free"
    assert completion.actual_model == "provider/actual-free-model"
    assert completion.provider_request_id == "request-safe"
    assert completion.usage and completion.usage.total_tokens == 15
    assert captured["http-referer"] == "https://example.test/docent/"
    assert captured["x-openrouter-title"] == "Docent"
    assert "test-only-key" not in captured["http-referer"] + captured["x-openrouter-title"]
    assert "reasoning" not in completion.model_dump_json()


@pytest.mark.asyncio
async def test_attribution_headers_are_absent_for_generic_configuration() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(request.headers)
        return _success(request)

    completion = await _provider(handler, model="operator/arbitrary-model:free").complete(
        system_prompt="system", user_prompt="user"
    )
    assert completion.configured_model == "operator/arbitrary-model:free"
    assert "http-referer" not in captured
    assert "x-openrouter-title" not in captured


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "exception"),
    [
        (401, ProviderAuthenticationError),
        (403, ProviderAuthorizationError),
        (429, ProviderRateLimitError),
        (503, ProviderModelUnavailableError),
    ],
)
async def test_provider_statuses_are_typed(status, exception) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"Retry-After": "999999"}, text="secret body")

    with pytest.raises(exception) as caught:
        await _provider(handler).complete(system_prompt="system", user_prompt="user")
    assert caught.value.retry_after == 3600
    assert "secret body" not in str(caught.value)


@pytest.mark.asyncio
async def test_timeout_and_malformed_shape_are_typed() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private timeout", request=request)

    with pytest.raises(ProviderTimeoutError):
        await _provider(timeout).complete(system_prompt="system", user_prompt="user")

    with pytest.raises(ProviderMalformedResponseError):
        await _provider(lambda request: httpx.Response(200, json={"choices": []})).complete(
            system_prompt="system", user_prompt="user"
        )


class CountingProvider:
    provider_label = "openai_compatible"
    configured_model = "openrouter/free"

    def __init__(self, completion: ProviderCompletion, failure: Exception | None = None):
        self.completion = completion
        self.failure = failure
        self.calls = 0

    async def complete(self, *, system_prompt: str, user_prompt: str) -> ProviderCompletion:
        self.calls += 1
        if self.failure:
            raise self.failure
        return self.completion


def _service(settings: Settings, provider: CountingProvider, budget=None) -> DocentService:
    record = DocentRecord(
        record_id="safe",
        record_type="test",
        subject_id="test",
        title="Safe record",
        content="bounded evidence",
        source=SourceLocator(document_id="test", authority="primary"),
        answer_policy="public",
        confidence="authoritative",
        version="1",
    )
    return DocentService(
        settings=settings,
        contract=load_contract(Path("config/docent.yaml")),
        retriever=LexicalRetriever([record]),
        provider=provider,
        deterministic_provider=MockProvider(),
        history=SessionHistory(settings.history_limit),
        live_budget=budget,
    )


def _completion(raw=None) -> ProviderCompletion:
    return ProviderCompletion(
        raw_content=raw
        or json.dumps(
            {
                "reply": "Synthesis",
                "record_ids": ["safe", "safe", "invented"],
                "grounded": True,
                "limitations": [],
            }
        ),
        configured_model="openrouter/free",
        actual_model="provider/actual",
        response_format_mode="json_object",
        duration_ms=1,
    )


@pytest.mark.asyncio
async def test_live_default_provenance_and_source_validation() -> None:
    provider = CountingProvider(_completion())
    settings = Settings(provider="openai_compatible", api_key="test", live_daily_budget=2)
    response = await _service(settings, provider).answer("session", "bounded evidence")
    assert response.provenance.inference_mode is InferenceMode.live
    assert response.provenance.configured_model == "openrouter/free"
    assert response.provenance.actual_model == "provider/actual"
    assert response.record_ids == ["safe"]
    assert response.grounded is True


@pytest.mark.asyncio
async def test_explicit_deterministic_does_not_call_or_spend_live_budget() -> None:
    provider = CountingProvider(_completion())
    settings = Settings(provider="openai_compatible", api_key="test", live_daily_budget=1)
    budget = InMemoryDailyBudget(1)
    service = _service(settings, provider, budget)
    response = await service.answer("session", "bounded evidence", InferenceMode.deterministic)
    assert response.provenance.inference_mode is InferenceMode.deterministic
    assert provider.calls == 0
    assert await budget.remaining() == 1


@pytest.mark.asyncio
async def test_disabled_modes_and_no_silent_fallback() -> None:
    mock_settings = Settings(provider="mock")
    live = CountingProvider(_completion())
    with pytest.raises(InferenceModeDisabledError):
        await _service(mock_settings, live).answer("s", "q", InferenceMode.live)

    disabled = Settings(
        provider="openai_compatible", api_key="test", allow_deterministic_mode=False
    )
    with pytest.raises(InferenceModeDisabledError):
        await _service(disabled, live).answer("s", "q", InferenceMode.deterministic)

    failure = CountingProvider(_completion(), ProviderRateLimitError())
    with pytest.raises(ProviderRateLimitError):
        await _service(
            Settings(provider="openai_compatible", api_key="test", live_daily_budget=2),
            failure,
        ).answer("s", "q")
    assert failure.calls == 1


@pytest.mark.asyncio
async def test_budget_counts_attempts_blocks_excess_and_resets_on_utc_day() -> None:
    now = [datetime(2026, 8, 5, tzinfo=UTC)]
    budget = InMemoryDailyBudget(2, now=lambda: now[0])
    assert await asyncio.gather(budget.reserve(), budget.reserve(), budget.reserve()) == [
        True,
        True,
        False,
    ]
    now[0] += timedelta(days=1)
    assert await budget.remaining() == 2

    provider = CountingProvider(_completion())
    service = _service(
        Settings(provider="openai_compatible", api_key="test", live_daily_budget=1),
        provider,
        InMemoryDailyBudget(1),
    )
    await service.answer("s", "bounded evidence")
    with pytest.raises(LiveBudgetExhaustedError):
        await service.answer("s", "bounded evidence")
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_failed_attempt_consumes_budget_and_does_not_modify_history() -> None:
    provider = CountingProvider(_completion(), ProviderRateLimitError())
    budget = InMemoryDailyBudget(1)
    service = _service(
        Settings(provider="openai_compatible", api_key="test", live_daily_budget=1),
        provider,
        budget,
    )
    with pytest.raises(ProviderRateLimitError):
        await service.answer("session", "bounded evidence")
    assert await budget.remaining() == 0
    assert await service.history.get("session") == []


@pytest.mark.asyncio
async def test_malformed_model_envelope_is_rejected_locally_without_history() -> None:
    provider = CountingProvider(_completion(raw="not a Docent envelope"))
    service = _service(
        Settings(provider="openai_compatible", api_key="test", live_daily_budget=1),
        provider,
    )
    with pytest.raises(ModelEnvelopeError):
        await service.answer("session", "bounded evidence")
    assert await service.history.get("session") == []


@pytest.mark.asyncio
async def test_disabled_budget_is_unlimited_and_not_reported_as_remaining() -> None:
    budget = InMemoryDailyBudget(0)
    assert await asyncio.gather(*(budget.reserve() for _ in range(20))) == [True] * 20
    assert await budget.remaining() is None
