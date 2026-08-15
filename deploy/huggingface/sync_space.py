from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
SPACE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
FILES = (
    "Dockerfile",
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "NOTICE",
    "ACKNOWLEDGMENTS.md",
)
DIRECTORIES = ("src", "config", "corpus", "sources", "development", "schemas")


def stage(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        source = ROOT / name
        if source.exists():
            shutil.copy2(source, destination / name)
    for name in DIRECTORIES:
        shutil.copytree(
            ROOT / name,
            destination / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
    shutil.copy2(ROOT / "deploy" / "huggingface" / "README.md", destination / "README.md")


def upload(repo_id: str, token: str) -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
        token=token,
    )
    with tempfile.TemporaryDirectory(prefix="docent-space-") as temporary:
        staged = Path(temporary)
        stage(staged)
        api.upload_folder(
            repo_id=repo_id,
            repo_type="space",
            folder_path=staged,
            delete_patterns="*",
            commit_message="Synchronize Docent public demo",
            token=token,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage or synchronize the Docent Docker Space")
    parser.add_argument("--space-id", default=os.environ.get("HF_SPACE_ID", ""))
    parser.add_argument("--stage-only", type=Path)
    args = parser.parse_args()
    if args.stage_only:
        stage(args.stage_only)
        return
    if not SPACE_ID.fullmatch(args.space_id):
        raise SystemExit("HF_SPACE_ID must have owner/name form.")
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is required as a narrowly scoped GitHub Actions secret.")
    upload(args.space_id, token)


if __name__ == "__main__":
    main()
