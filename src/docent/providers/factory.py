from __future__ import annotations

from docent.config import Settings
from docent.providers.base import ModelProvider
from docent.providers.mock import MockProvider
from docent.providers.openai_compatible import OpenAICompatibleProvider


def build_provider(settings: Settings) -> ModelProvider:
    provider = settings.provider.casefold()
    if provider == "mock":
        return MockProvider()
    if provider == "openai_compatible":
        if not settings.api_key:
            raise RuntimeError("DOCENT_API_KEY is required for openai_compatible provider")
        return OpenAICompatibleProvider(
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=settings.model,
            max_output_tokens=settings.max_output_tokens,
            temperature=settings.temperature,
            timeout_seconds=settings.request_timeout_seconds,
            site_url=settings.site_url,
            app_title=settings.app_title,
        )
    raise RuntimeError(f"Unsupported DOCENT_PROVIDER: {settings.provider}")
