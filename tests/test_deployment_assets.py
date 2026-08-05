from pathlib import Path

from deploy.huggingface.sync_space import SPACE_ID, stage

ROOT = Path(__file__).parents[1]


def test_dockerfile_runs_as_non_root_and_preserves_port_and_health() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "USER docent" in dockerfile
    assert "EXPOSE 7860" in dockerfile
    assert "127.0.0.1:7860/health" in dockerfile
    assert "COPY development ./development" in dockerfile


def test_space_staging_contains_only_intended_runtime_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sentinel = "token-value-must-never-be-staged"
    monkeypatch.setenv("HF_TOKEN", sentinel)
    destination = tmp_path / "space"
    stage(destination)
    staged = {path.relative_to(destination).as_posix() for path in destination.rglob("*")}

    assert "README.md" in staged
    assert "Dockerfile" in staged
    assert "src/docent/app.py" in staged
    assert "development/capabilities.yaml" in staged
    assert ".github" not in staged
    assert ".git" not in staged
    assert all(
        sentinel not in path.read_text(encoding="utf-8", errors="ignore")
        for path in destination.rglob("*")
        if path.is_file()
    )


def test_hugging_face_workflow_uses_secret_and_variable_without_identity() -> None:
    workflow = (ROOT / ".github" / "workflows" / "huggingface-space.yml").read_text(
        encoding="utf-8"
    )

    assert "${{ secrets.HF_TOKEN }}" in workflow
    assert "${{ vars.HF_SPACE_ID }}" in workflow
    assert "PaulTiffany/" not in workflow
    assert SPACE_ID.fullmatch("owner/space-name")
    assert not SPACE_ID.fullmatch("space-name")


def test_pages_workflow_uses_public_repository_variable() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")

    assert "${{ vars.DOCENT_API_BASE_URL }}" in workflow
    assert "secrets." not in workflow
    assert "actions/deploy-pages@v4" in workflow
