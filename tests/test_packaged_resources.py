from pathlib import Path

from fastapi.testclient import TestClient

from docent.config import Settings, load_contract
from docent.corpus import load_records
from docent.development import load_development_manifest
from docent.resources import default_resource, default_resource_root


def test_packaged_defaults_resolve_outside_repository(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    settings = Settings(_env_file=None)
    contract = load_contract(settings.contract_path)
    records = load_records(settings.corpus_path)
    manifest = load_development_manifest(settings.development_root)

    assert contract.identity.name
    assert records
    assert any(record.record_id == "openbgi.article-xi" for record in records)
    assert manifest.pathways
    assert default_resource("corpus/self-docent.jsonl").exists()
    assert default_resource("corpus/reference.collection.json").exists()
    assert default_resource("sources/openbgi-constitution.lock.json").exists()
    assert default_resource("sources/openbgi-constitution/draft-0.6/article-xi.txt").exists()
    assert (default_resource_root() / "development" / "capabilities.yaml").exists()


def test_installed_style_app_health_uses_packaged_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    # Import after changing directory to exercise the installed-package resource resolver.
    from docent.app import app

    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
