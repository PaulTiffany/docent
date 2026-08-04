from __future__ import annotations

import json
import re


class MockProvider:
    """Deterministic no-key provider for local smoke tests and demonstrations."""

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        match = re.search(
            r"BEGIN RETRIEVED PUBLIC RECORDS\s*(\[.*?\])\s*END RETRIEVED PUBLIC RECORDS",
            user_prompt,
            flags=re.DOTALL,
        )
        records: list[dict] = []
        if match:
            try:
                parsed = json.loads(match.group(1))
                if isinstance(parsed, list):
                    records = [item for item in parsed if isinstance(item, dict)]
            except json.JSONDecodeError:
                records = []

        if records:
            top = records[0]
            payload = {
                "reply": str(top.get("content") or top.get("title") or "Relevant record found."),
                "record_ids": [str(top["record_id"])] if top.get("record_id") else [],
                "grounded": True,
                "limitations": [
                    "Deterministic mock mode returns the top retrieved record without model synthesis."
                ],
            }
        else:
            payload = {
                "reply": "I do not have enough support in the configured collection to answer that reliably.",
                "record_ids": [],
                "grounded": True,
                "limitations": ["No relevant public record was retrieved."],
            }
        return json.dumps(payload)
