from pathlib import Path

from docent.corpus import load_records


def test_example_corpus_loads() -> None:
    records = load_records(Path("corpus/records.jsonl"))
    assert len(records) >= 4
    assert len({record.record_id for record in records}) == len(records)
    assert all(record.answer_policy == "public" for record in records)
