from __future__ import annotations

from pathlib import Path

DEFAULT_SCAN_ROOTS = ("src", "config", "schemas", "examples", "tests/fixtures")


def load_denylist(path: Path) -> list[str]:
    return [
        line.strip().casefold()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def audit_content(
    repository: Path, denylist_path: Path, scan_roots: tuple[str, ...] = DEFAULT_SCAN_ROOTS
) -> list[str]:
    denied = load_denylist(denylist_path)
    violations: list[str] = []
    for root_name in scan_roots:
        root = repository / root_name
        if not root.exists():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path.resolve() == denylist_path.resolve():
                continue
            try:
                text = path.read_text(encoding="utf-8-sig").casefold()
            except UnicodeDecodeError:
                continue
            for term in denied:
                if term in text:
                    violations.append(
                        f"{path.relative_to(repository)}: contains denied identifier {term!r}"
                    )
    return violations


def main() -> None:
    repository = Path.cwd()
    violations = audit_content(repository, repository / "config/content-denylist.txt")
    if violations:
        raise SystemExit("Content-boundary audit failed:\n" + "\n".join(violations))
    print("Content-boundary audit passed.")


if __name__ == "__main__":
    main()
