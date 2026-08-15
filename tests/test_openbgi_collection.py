import hashlib
import json
from pathlib import Path

from docent.corpus import load_records
from docent.openbgi import CANONICAL_URL, DOCUMENT_ID, SECTION_SPECS, canonicalize
from docent.retrieval import LexicalRetriever


def test_reference_collection_includes_verified_openbgi_sections() -> None:
    records = load_records(Path("corpus/reference.collection.json"))
    openbgi = [record for record in records if record.subject_id == "openbgi-constitution"]
    record_ids = {record.record_id for record in records}
    assert len(openbgi) == len(SECTION_SPECS) == 16
    assert "docent.identity" in record_ids
    assert "docent.openrouter-gateway" not in record_ids
    assert "docent.live-budget" not in record_ids

    lock = json.loads(Path("sources/openbgi-constitution.lock.json").read_text(encoding="utf-8"))
    locked = {row["key"]: row for row in lock["sections"]}
    for record in openbgi:
        key = record.record_id.removeprefix("openbgi.")
        assert record.source.document_id == DOCUMENT_ID
        assert str(record.source.url) == CANONICAL_URL
        assert record.source.authority == "primary"
        assert record.version == "Draft 0.6"
        served = canonicalize(record.content)
        assert hashlib.sha256(served.encode("utf-8")).hexdigest() == locked[key]["sha256"]


def test_openbgi_question_forms_retrieve_the_expected_source_section() -> None:
    retriever = LexicalRetriever(load_records(Path("corpus/reference.collection.json")))

    wisdom = retriever.search("What is the Wisdom Clause?", limit=1)
    assert wisdom[0].record.record_id == "openbgi.article-xi"

    capture = retriever.search("What are the anti-capture tripwires?", limit=1)
    assert capture[0].record.record_id == "openbgi.article-vi"
