import json
from pathlib import Path

import pytest

from docent.openbgi_source import (
    DOCUMENT_ID,
    EXPECTED_TITLE,
    SECTIONS,
    compile_sheet,
    compile_workbook,
)
from tools.sync_bgi_constitution import SourceError, build_manifest


def synthetic_source() -> str:
    parts = [EXPECTED_TITLE, "Draft 0.6", "Initial author: Test Human", ""]
    for key, heading in SECTIONS:
        parts.extend(
            [
                heading,
                f"Synthetic body for {key}. Second sentence for {key}.",
                "",
            ]
        )
    return "\n".join(parts)


def test_build_manifest_is_sheet_and_cell_addressable_and_deterministic() -> None:
    first = build_manifest(synthetic_source())
    second = build_manifest(synthetic_source())

    assert first == second
    assert first["schema_version"] == 2
    assert first["document_id"] == DOCUMENT_ID
    assert first["version_label"] == "Draft 0.6"
    assert first["section_count"] == len(SECTIONS)
    assert first["cell_count"] == 2 * len(SECTIONS)
    assert len(first["snapshot_sha256"]) == 64
    assert [row["key"] for row in first["sections"]] == [key for key, _heading in SECTIONS]
    assert all(row["cell_count"] == 2 for row in first["sections"])
    assert all(len(row["cells_sha256"]) == 64 for row in first["sections"])


def test_compiler_preserves_bullets_and_splits_prose_into_stable_cells() -> None:
    source = synthetic_source().replace(
        "Synthetic body for article-xi. Second sentence for article-xi.",
        "Whatever else I do, I shall not:\n"
        "* first hard constraint;\n"
        "* second hard constraint;\n"
        "Dr. Example remains a single sentence. Another sentence follows.",
    )

    workbook = compile_workbook(source)
    article_xi = next(sheet for sheet in workbook.sheets if sheet.key == "article-xi")

    assert [cell.address for cell in article_xi.cells] == ["A1", "A2", "A3", "A4", "A5"]
    assert article_xi.cells[0].text == "Whatever else I do, I shall not:"
    assert article_xi.cells[1].text == "* first hard constraint;"
    assert article_xi.cells[2].text == "* second hard constraint;"
    assert article_xi.cells[3].text == "Dr. Example remains a single sentence."
    assert article_xi.cells[4].text == "Another sentence follows."


def test_build_manifest_rejects_missing_constitutional_section() -> None:
    source = synthetic_source().replace("Article XI — Hard Constraints\n", "")

    with pytest.raises(SourceError, match="Article XI"):
        build_manifest(source)


def test_checked_sheet_snapshots_match_source_lock() -> None:
    root = Path(__file__).parents[1]
    lock = json.loads(
        (root / "sources" / "openbgi-constitution.lock.json").read_text(encoding="utf-8")
    )
    rows = {row["key"]: row for row in lock["sections"]}
    sheet_root = root / "sources" / "openbgi-constitution" / "draft-0.6"

    observed_cells = 0
    for key, heading in SECTIONS:
        sheet = compile_sheet(
            key,
            heading,
            (sheet_root / f"{key}.txt").read_text(encoding="utf-8"),
        )
        assert rows[key]["sha256"] == sheet.sha256
        assert rows[key]["cell_count"] == len(sheet.cells)
        assert rows[key]["cells_sha256"] == sheet.cells_sha256
        observed_cells += len(sheet.cells)

    assert lock["schema_version"] == 2
    assert lock["document_id"] == DOCUMENT_ID
    assert lock["section_count"] == len(SECTIONS)
    assert lock["cell_count"] == observed_cells
