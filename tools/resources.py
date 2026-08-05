from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
OUTPUT = ROOT / "src" / "docent" / "resources"
FILES = {
    ROOT / "config" / "docent.yaml": OUTPUT / "config" / "docent.yaml",
    ROOT / "corpus" / "self-docent.jsonl": OUTPUT / "corpus" / "self-docent.jsonl",
}
DIRECTORIES = {
    ROOT / "development": OUTPUT / "development",
}


def drift() -> list[str]:
    differences: list[str] = []
    for source, target in FILES.items():
        if not target.exists() or source.read_bytes() != target.read_bytes():
            differences.append(target.relative_to(ROOT).as_posix())
    for source, target in DIRECTORIES.items():
        comparison = filecmp.dircmp(source, target)
        if (
            comparison.left_only
            or comparison.right_only
            or comparison.diff_files
            or comparison.funny_files
        ):
            differences.append(target.relative_to(ROOT).as_posix())
        for subdirectory in comparison.subdirs.values():
            if subdirectory.left_only or subdirectory.right_only or subdirectory.diff_files:
                differences.append(target.relative_to(ROOT).as_posix())
                break
    return sorted(set(differences))


def synchronize() -> None:
    for source, target in FILES.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for source, target in DIRECTORIES.items():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or verify packaged default resources")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        differences = drift()
        if differences:
            print(
                "Packaged default resources have drifted:\n" + "\n".join(differences),
                file=sys.stderr,
            )
            raise SystemExit(1)
        return
    synchronize()
    print("Synchronized default resources into the Python package.")


if __name__ == "__main__":
    main()
