from __future__ import annotations

from typing import Protocol

from docent.models import ProviderCompletion


class ModelProvider(Protocol):
    provider_label: str
    configured_model: str

    async def complete(self, *, system_prompt: str, user_prompt: str) -> ProviderCompletion: ...
