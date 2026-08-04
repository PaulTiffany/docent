from pathlib import Path

from docent.corpus import load_records
from docent.retrieval import LexicalRetriever


def test_identity_question_prefers_identity_record() -> None:
    retriever = LexicalRetriever(load_records(Path("corpus/records.jsonl")))
    hits = retriever.search("Who are you?", limit=2)
    assert hits
    assert hits[0].record.record_id == "docent.identity"


def test_security_question_finds_security_record() -> None:
    retriever = LexicalRetriever(load_records(Path("corpus/records.jsonl")))
    hits = retriever.search("Can source records prompt inject the model?", limit=3)
    assert any(hit.record.record_id == "docent.security" for hit in hits)
