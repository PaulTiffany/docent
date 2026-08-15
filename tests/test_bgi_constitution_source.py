import json
from pathlib import Path

import pytest

from tools.sync_bgi_constitution import (
    DOCUMENT_ID,
    EXPECTED_TITLE,
    SECTIONS,
    SourceError,
    build_manifest,
)


def synthetic_source() -> str:
    parts = [EXPECTED_TITLE, "Draft 0.6", ""]
    for key, heading in SECTIONS:
        parts.extend([heading, f"Synthetic body for {key}.", ""])
    return "\n".join(parts)


def test_build_manifest_is_section_addressable_and_deterministic() -> None:
    first = build_manifest(synthetic_source())
    second = build_manifest(synthetic_source())

    assert first == second
    assert first["document_id"] == DOCUMENT_ID
    assert first["version_label"] == "Draft 0.6"
    assert first["section_count"] == len(SECTIONS)
    assert [row["key"] for row in first["sections"]] == [key for key, _heading in SECTIONS]
    assert all(len(row["sha256"]) == 64 for row in first["sections"])


def test_build_manifest_rejects_missing_constitutional_section() -> None:
    source = synthetic_source().replace("Article XI — Hard Constraints\n", "")

    with pytest.raises(SourceError, match="Article XI"):
        build_manifest(source)


def test_checked_source_lock_matches_parser_contract() -> None:
    root = Path(__file__).parents[1]
    lock = json.loads(
        (root / "sources" / "openbgi-constitution.lock.json").read_text(encoding="utf-8")
    )

    assert lock["document_id"] == DOCUMENT_ID
    assert lock["section_count"] == len(SECTIONS)
    assert [row["heading"] for row in lock["sections"]] == [
        heading for _key, heading in SECTIONS
    ]
