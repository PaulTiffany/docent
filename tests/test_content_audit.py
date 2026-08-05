from pathlib import Path

from docent.content_audit import audit_content


def test_repository_passes_content_boundary_audit() -> None:
    root = Path.cwd()
    assert audit_content(root, root / "config/content-denylist.txt") == []


def test_content_boundary_audit_detects_configured_identifier(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "example.py").write_text("forbidden-marker", encoding="utf-8")
    denylist = tmp_path / "denylist.txt"
    denylist.write_text("forbidden-marker\n", encoding="utf-8")
    violations = audit_content(tmp_path, denylist, ("src",))
    assert len(violations) == 1
    assert "src\\example.py" in violations[0] or "src/example.py" in violations[0]
