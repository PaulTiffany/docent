from __future__ import annotations

import json
import re
import time

from docent.models import ProviderCompletion


def _deterministic_reply(record: dict) -> str:
    content = str(record.get("content") or record.get("title") or "Relevant record found.").strip()
    record_type = str(record.get("record_type") or "")
    title = str(record.get("title") or "").strip()
    if record_type not in {"constitution-sheet", "constitution-cell"} or not title:
        return content

    label = title.split(" · ", 1)[0].strip()
    if record_type == "constitution-sheet":
        lines = content.splitlines()
        if lines and lines[0].strip() == label:
            content = "\n".join(lines[1:]).strip()
    return f"{label}: {content}" if content else label


class MockProvider:
    """Deterministic no-key provider for tests, offline use, and corpus debugging."""

    provider_label = "mock"
    configured_model = "deterministic-corpus"

    async def complete(self, *, system_prompt: str, user_prompt: str) -> ProviderCompletion:
        started = time.monotonic()
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
                "reply": _deterministic_reply(top),
                "record_ids": [str(top["record_id"])] if top.get("record_id") else [],
                "grounded": True,
                "limitations": [
                    "Deterministic corpus mode returns the top retrieved source record with display-only formatting and no model inference."
                ],
            }
        else:
            payload = {
                "reply": "I do not have enough support in the configured collection to answer that reliably.",
                "record_ids": [],
                "grounded": False,
                "limitations": ["No relevant public record was retrieved."],
            }
        return ProviderCompletion(
            raw_content=json.dumps(payload),
            configured_model=self.configured_model,
            actual_model=self.configured_model,
            finish_reason="deterministic",
            response_format_mode="deterministic",
            duration_ms=max(int((time.monotonic() - started) * 1000), 0),
        )
