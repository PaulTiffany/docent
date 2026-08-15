from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from docent.models import DocentRecord
from docent.openbgi import OpenBGISnapshotError, load_openbgi_records


class CorpusError(RuntimeError):
    pass


def _load_jsonl(path: Path) -> list[DocentRecord]:
    if not path.is_file():
        raise CorpusError(f"Corpus file does not exist: {path}")

    records: list[DocentRecord] = []
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(DocentRecord.model_validate(json.loads(line)))
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                errors.append(f"{path.name} line {line_number}: {exc}")
    if errors:
        raise CorpusError("Invalid corpus:\n" + "\n".join(errors))
    return records


def _resolve_under_root(root: Path, base: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise CorpusError("Collection paths must be non-empty relative paths")
    resolved_root = root.resolve()
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CorpusError(f"Collection path escapes its resource root: {relative}") from exc
    return resolved


def _load_collection(path: Path) -> list[DocentRecord]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusError(f"Invalid collection manifest: {path}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise CorpusError("Collection manifest must use schema_version 1")

    files = manifest.get("files", [])
    builtins = manifest.get("builtins", [])
    excluded = manifest.get("exclude_record_ids", [])
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        raise CorpusError("Collection files must be a list of relative paths")
    if not isinstance(builtins, list) or not all(isinstance(item, dict) for item in builtins):
        raise CorpusError("Collection builtins must be a list of objects")
    if not isinstance(excluded, list) or not all(isinstance(item, str) for item in excluded):
        raise CorpusError("Collection exclude_record_ids must be a list of record IDs")
    if len(set(excluded)) != len(excluded):
        raise CorpusError("Collection exclude_record_ids contains duplicates")

    root = path.parent.parent
    records: list[DocentRecord] = []
    for relative in files:
        records.extend(_load_jsonl(_resolve_under_root(root, path.parent, relative)))

    for builtin in builtins:
        if builtin.get("kind") != "openbgi-constitution":
            raise CorpusError(f"Unknown collection builtin: {builtin.get('kind')!r}")
        source_root = builtin.get("source_root")
        lock = builtin.get("lock")
        if not isinstance(source_root, str) or not isinstance(lock, str):
            raise CorpusError("OpenBGI builtin requires source_root and lock paths")
        try:
            records.extend(
                load_openbgi_records(
                    _resolve_under_root(root, path.parent, source_root),
                    _resolve_under_root(root, path.parent, lock),
                )
            )
        except (OSError, json.JSONDecodeError, OpenBGISnapshotError, ValidationError) as exc:
            raise CorpusError(f"Invalid OpenBGI worked example: {exc}") from exc

    excluded_ids = set(excluded)
    available_ids = {record.record_id for record in records}
    missing_exclusions = excluded_ids - available_ids
    if missing_exclusions:
        raise CorpusError(
            "Collection excludes unknown record IDs: " + ", ".join(sorted(missing_exclusions))
        )
    return [record for record in records if record.record_id not in excluded_ids]


def load_records(path: Path) -> list[DocentRecord]:
    if not path.exists():
        raise CorpusError(f"Corpus file does not exist: {path}")

    records = (
        _load_collection(path) if path.name.endswith(".collection.json") else _load_jsonl(path)
    )
    if not records:
        raise CorpusError("Corpus contains no records")

    seen: set[str] = set()
    duplicates: list[str] = []
    for record in records:
        if record.record_id in seen:
            duplicates.append(record.record_id)
        seen.add(record.record_id)
    if duplicates:
        raise CorpusError(
            "Duplicate record IDs across collection: " + ", ".join(sorted(set(duplicates)))
        )
    return records
