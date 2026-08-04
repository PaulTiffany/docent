from __future__ import annotations

import httpx


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_output_tokens: int,
        temperature: float,
        timeout_seconds: float,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Model provider returned an unexpected response shape") from exc
