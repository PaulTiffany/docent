import hashlib
import json
from pathlib import Path

from docent.corpus import load_records
from docent.openbgi import CANONICAL_URL, DOCUMENT_ID, SECTION_SPECS
from docent.openbgi_source import canonicalize, compile_workbook
from docent.retrieval import LexicalRetriever


def test_reference_collection_includes_verified_openbgi_sheets_and_cells() -> None:
    records = load_records(Path("corpus/reference.collection.json"))
    openbgi = [record for record in records if record.subject_id == "openbgi-constitution"]
    sheets = [record for record in openbgi if record.record_type == "constitution-sheet"]
    cells = [record for record in openbgi if record.record_type == "constitution-cell"]
    record_ids = {record.record_id for record in records}

    lock = json.loads(Path("sources/openbgi-constitution.lock.json").read_text(encoding="utf-8"))
    assert len(sheets) == len(SECTION_SPECS) + 1 == 17
    assert len(cells) == lock["cell_count"]
    assert len(openbgi) == len(sheets) + len(cells)
    assert "openbgi.front-matter" in record_ids
    assert "openbgi.front-matter.A3" in record_ids
    assert "docent.identity" in record_ids
    assert "docent.openrouter-gateway" not in record_ids
    assert "docent.live-budget" not in record_ids

    locked = {row["key"]: row for row in lock["sections"]}
    for record in sheets:
        assert record.source.document_id == DOCUMENT_ID
        assert str(record.source.url) == CANONICAL_URL
        assert record.source.authority == "primary"
        assert record.version == "Draft 0.6"
        served = canonicalize(record.content)
        digest = hashlib.sha256(served.encode("utf-8")).hexdigest()
        if record.record_id == "openbgi.front-matter":
            assert digest == lock["front_matter"]["sha256"]
        else:
            key = record.record_id.removeprefix("openbgi.")
            assert digest == locked[key]["sha256"]


def test_openbgi_cells_are_derived_from_checked_document_snapshot() -> None:
    snapshot = Path("sources/openbgi-constitution/draft-0.6/document.txt")
    workbook = compile_workbook(snapshot.read_text(encoding="utf-8"))
    records = load_records(Path("corpus/reference.collection.json"))
    record_map = {record.record_id: record for record in records}

    for sheet in workbook.sheets:
        for cell in sheet.cells:
            record = record_map[f"openbgi.{sheet.key}.{cell.address}"]
            assert record.content == cell.text
            assert record.source.section == f"{sheet.heading} [{cell.address}]"
            assert any(cell.sha256 in boundary for boundary in record.boundaries)
            assert any(
                f"Document part: {sheet.part}." == boundary for boundary in record.boundaries
            )


def test_openbgi_question_forms_retrieve_expected_source_sheet_or_cell() -> None:
    retriever = LexicalRetriever(load_records(Path("corpus/reference.collection.json")))

    author = retriever.search("Who wrote the OpenBGI Constitution?", limit=1)
    assert author[0].record.record_id == "openbgi.front-matter.A3"
    assert author[0].record.content == "Initial author: Ben Goertzel (human)"

    contributor = retriever.search("Who else contributed to the OpenBGI Constitution?", limit=1)
    assert contributor[0].record.record_id == "openbgi.front-matter.A4"

    wisdom = retriever.search("What is the Wisdom Clause?", limit=1)
    assert wisdom[0].record.record_id.startswith("openbgi.article-xi")

    capture = retriever.search("What are the anti-capture tripwires?", limit=1)
    assert capture[0].record.record_id.startswith("openbgi.article-vi")

    exact = retriever.search("Escalation within a capturing entity is not escalation.", limit=1)
    assert exact[0].record.record_id.startswith("openbgi.article-vi.A")
