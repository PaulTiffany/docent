from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from docent.models import DocentRecord


class CorpusError(RuntimeError):
    pass


def load_records(path: Path) -> list[DocentRecord]:
    if not path.exists():
        raise CorpusError(f"Corpus file does not exist: {path}")

    records: list[DocentRecord] = []
    seen: set[str] = set()
    errors: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                record = DocentRecord.model_validate(raw)
                if record.record_id in seen:
                    raise ValueError(f"duplicate record_id {record.record_id!r}")
                seen.add(record.record_id)
                records.append(record)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                errors.append(f"line {line_number}: {exc}")

    if errors:
        raise CorpusError("Invalid corpus:\n" + "\n".join(errors))
    if not records:
        raise CorpusError("Corpus contains no records")
    return records
