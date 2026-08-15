from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import docent.app as app_module
from docent.models import InferenceMode
from docent.providers.errors import ProviderRateLimitError


def test_public_config_is_strict_safe_and_does_not_fabricate_actual_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module.settings, "provider", "openai_compatible")
    monkeypatch.setattr(app_module.settings, "api_key", "test-private-key")
    monkeypatch.setattr(app_module.settings, "model", "openrouter/free")
    monkeypatch.setattr(app_module.settings, "base_url", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(app_module.settings, "app_title", "Docent")
    monkeypatch.setattr(app_module.settings, "allow_deterministic_mode", True)

    response = TestClient(app_module.app).get("/api/config/public")
    assert response.status_code == 200
    body = response.json()
    assert body["default_inference_mode"] == "live"
    assert body["enabled_inference_modes"] == ["live", "deterministic"]
    assert body["provider"] == "openrouter"
    assert body["configured_model"] == "openrouter/free"
    assert "actual_model" not in body
    assert "test-private-key" not in response.text
    assert "base_url" not in response.text


def test_omitted_mode_remains_backward_compatible_and_invalid_mode_is_rejected() -> None:
    client = TestClient(app_module.app)
    response = client.post("/api/chat", json={"session_id": "compat", "message": "What is Docent?"})
    assert response.status_code == 200
    assert response.json()["provenance"]["inference_mode"] == "deterministic"

    invalid = client.post(
        "/api/chat",
        json={"session_id": "compat", "message": "What is Docent?", "mode": "magic"},
    )
    assert invalid.status_code == 422


def test_public_provider_error_is_bounded_and_does_not_fabricate_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(session_id, message, mode=None):
        raise ProviderRateLimitError("raw upstream body and private diagnostics", retry_after=12)

    monkeypatch.setattr(app_module.service, "answer", fail)
    response = TestClient(app_module.app).post(
        "/api/chat",
        json={"session_id": "failure", "message": "Synthesize", "mode": "live"},
    )
    assert response.status_code == 429
    assert response.json()["detail"] == {
        "code": "live_inference_rate_limited",
        "message": "The live inference allowance is temporarily exhausted.",
        "retry_after_seconds": 12,
    }
    assert "raw upstream" not in response.text
    assert "reply" not in response.json()


def test_model_key_is_absent_from_public_and_deployment_assets() -> None:
    roots = [
        Path("web"),
        Path("docs"),
        Path("src/docent/static"),
        Path(".github/workflows"),
        Path("deploy/huggingface"),
    ]
    forbidden_assignments = ("DOCENT_API_KEY=sk-", "OPENROUTER_API_KEY=", "Bearer sk-")
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {
                ".html",
                ".js",
                ".css",
                ".json",
                ".yml",
                ".yaml",
                ".md",
                ".py",
            }:
                text = path.read_text(encoding="utf-8")
                assert not any(fragment in text for fragment in forbidden_assignments)


def test_inference_mode_enum_is_only_live_or_deterministic() -> None:
    assert [mode.value for mode in InferenceMode] == ["live", "deterministic"]


def test_deterministic_constitution_stub_uses_document_structure() -> None:
    client = TestClient(app_module.app)

    authorship = client.post(
        "/api/chat",
        json={
            "session_id": "constitution-author",
            "message": "Who wrote the OpenBGI Constitution?",
            "mode": "deterministic",
        },
    )
    assert authorship.status_code == 200
    assert authorship.json()["reply"] == "Front Matter: Initial author: Ben Goertzel (human)"
    assert authorship.json()["record_ids"] == ["openbgi.front-matter.A3"]

    caveats = client.post(
        "/api/chat",
        json={
            "session_id": "constitution-caveats",
            "message": "What does Caveats say?",
            "mode": "deterministic",
        },
    )
    assert caveats.status_code == 200
    assert caveats.json()["reply"].startswith("Caveats: This Constitution is both ambitious")
    assert caveats.json()["record_ids"] == ["openbgi.caveats"]
