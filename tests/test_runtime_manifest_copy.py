import shutil
from pathlib import Path

from docent.development import load_development_manifest

ROOT = Path(__file__).parents[1]


def test_runtime_manifest_copy_does_not_require_development_only_evidence(
    tmp_path: Path,
) -> None:
    shutil.copytree(ROOT / "development", tmp_path / "development")
    (tmp_path / "pyproject.toml").write_text("runtime image marker", encoding="utf-8")

    manifest = load_development_manifest(tmp_path)

    assert manifest.capabilities
