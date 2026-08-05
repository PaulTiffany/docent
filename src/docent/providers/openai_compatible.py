from __future__ import annotations

import time
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from docent.models import ProviderCompletion, TokenUsage
from docent.providers.errors import (
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderConnectionError,
    ProviderMalformedResponseError,
    ProviderModelUnavailableError,
    ProviderNoCompatibleModelError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

_SAFE_TEXT_LIMIT = 256
_MAX_RETRY_AFTER = 3600


def _safe_text(value: Any, limit: int = _SAFE_TEXT_LIMIT) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split()).strip()
    return value[:limit] or None


def _retry_after_seconds(value: str | None) -> int | None:
    if not value:
        return None
    try:
        seconds = int(value)
    except ValueError:
        try:
            target = parsedate_to_datetime(value)
            seconds = int(target.timestamp() - time.time())
        except (TypeError, ValueError, OverflowError):
            return None
    return min(max(seconds, 0), _MAX_RETRY_AFTER)


def _bounded_token(value: Any) -> int | None:
    return value if isinstance(value, int) and 0 <= value <= 100_000_000 else None


class OpenAICompatibleProvider:
    provider_label = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_output_tokens: int,
        temperature: float,
        timeout_seconds: float,
        site_url: str | None = None,
        app_title: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.provider_label = (
            "openrouter"
            if base_url.strip().rstrip("/").casefold() == "https://openrouter.ai/api/v1"
            else "openai_compatible"
        )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.configured_model = model
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.site_url = site_url
        self.app_title = app_title
        self.transport = transport

    def request_headers(self) -> dict[str, str]:
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_title:
            headers["X-OpenRouter-Title"] = self.app_title
        return headers

    async def complete(self, *, system_prompt: str, user_prompt: str) -> ProviderCompletion:
        started = time.monotonic()
        payload = {
            "model": self.configured_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, transport=self.transport
            ) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.request_headers(),
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("provider request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderConnectionError("provider connection failed") from exc

        retry_after = _retry_after_seconds(response.headers.get("retry-after"))
        if response.status_code == 401:
            raise ProviderAuthenticationError(retry_after=retry_after)
        if response.status_code == 403:
            raise ProviderAuthorizationError(retry_after=retry_after)
        if response.status_code == 429:
            raise ProviderRateLimitError(retry_after=retry_after)
        if response.status_code in {404, 409, 422}:
            raise ProviderNoCompatibleModelError(retry_after=retry_after)
        if response.status_code in {408, 502, 503, 504}:
            raise ProviderModelUnavailableError(retry_after=retry_after)
        if response.is_error:
            raise ProviderConnectionError(retry_after=retry_after)

        try:
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("missing content")
            usage_body = body.get("usage") or {}
            usage = TokenUsage(
                prompt_tokens=_bounded_token(usage_body.get("prompt_tokens")),
                completion_tokens=_bounded_token(usage_body.get("completion_tokens")),
                total_tokens=_bounded_token(usage_body.get("total_tokens")),
            )
            if usage.prompt_tokens is usage.completion_tokens is usage.total_tokens is None:
                usage = None
            return ProviderCompletion(
                raw_content=content,
                configured_model=self.configured_model,
                actual_model=_safe_text(body.get("model")),
                provider_request_id=_safe_text(body.get("id")),
                finish_reason=_safe_text(choice.get("finish_reason"), 128),
                usage=usage,
                response_format_mode="json_object",
                duration_ms=max(int((time.monotonic() - started) * 1000), 0),
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderMalformedResponseError("unexpected provider response shape") from exc
