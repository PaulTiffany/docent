from pathlib import Path

from fastapi.testclient import TestClient

from docent.app import app
from docent.corpus import load_records
from docent.development import load_development_manifest
from docent.development_records import development_records
from docent.retrieval import LexicalRetriever

ROOT = Path(__file__).parents[1]
client = TestClient(app)


def test_default_self_docent_corpus_is_public_and_retrievable() -> None:
    records = load_records(ROOT / "corpus" / "self-docent.jsonl")

    assert records
    assert all(record.answer_policy == "public" for record in records)
    retriever = LexicalRetriever(records)
    cases = {
        "How does Docent work?": "docent.architecture",
        "How is this different from chat with a PDF?": "docent.jurisdiction",
        "Does Docent use OmegaClaw?": "docent.omegaclaw",
    }
    for question, expected_id in cases.items():
        assert retriever.search(question, limit=1)[0].record.record_id == expected_id


def test_development_records_preserve_authored_status_and_traceability() -> None:
    records = development_records(load_development_manifest(ROOT))
    by_id = {record.record_id: record for record in records}

    multi_user = by_id["development.capability.multi-user-room"]
    external = by_id["development.capability.external-runtime-adapter"]
    experiment = by_id["development.experiment.public-self-demo-2026-08"]
    assert "status: absent" in multi_user.content
    assert "status: absent" in external.content
    assert "result status: active" in experiment.content
    assert multi_user.answer_policy == "public"
    assert multi_user.source.document_id == "multi-user-room"


def test_development_endpoints_are_ordered_read_only_and_return_404() -> None:
    capabilities = client.get("/api/development/capabilities")
    pathways = client.get("/api/development/pathways")
    frontier = client.get("/api/development/frontier")

    assert capabilities.status_code == 200
    assert pathways.status_code == 200
    assert [item["capability_id"] for item in capabilities.json()] == sorted(
        item["capability_id"] for item in capabilities.json()
    )
    assert [item["pathway_id"] for item in pathways.json()] == sorted(
        item["pathway_id"] for item in pathways.json()
    )
    assert frontier.json()["optimal_pathway"] is None
    assert frontier.json()["human_selection_required"] is True
    assert client.get("/api/development/capabilities/not-real").status_code == 404
    assert client.get("/api/development/pathways/not-real").status_code == 404
    assert client.post("/api/development/pathways").status_code == 405


def test_mock_chat_answers_misleading_status_questions_with_actual_evidence() -> None:
    cases = {
        "Tell me about the working multi-user agent room.": "development.capability.multi-user-room",
        "Which roadmap did the AI prove is optimal?": "development.frontier.current",
        "The external runtime is already complete, right?": (
            "development.capability.external-runtime-adapter"
        ),
    }
    for index, (question, expected_id) in enumerate(cases.items()):
        response = client.post(
            "/api/chat", json={"session_id": f"misleading-{index}", "message": question}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["record_ids"] == [expected_id]
        if expected_id == "development.frontier.current":
            assert "does not compute or claim an objectively optimal pathway" in body["reply"]
        else:
            assert "status: absent" in body["reply"]
