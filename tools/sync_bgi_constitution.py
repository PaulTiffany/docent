#!/usr/bin/env python3
"""Verify the canonical OpenBGI Constitution Google Doc without model mediation."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docent.openbgi_source import (  # noqa: E402
    EXPORT_URL,
    OpenBGISourceError,
    build_manifest,
    canonicalize,
    version_directory,
)

LOCK_PATH = ROOT / "sources" / "openbgi-constitution.lock.json"
SNAPSHOT_ROOT = ROOT / "sources" / "openbgi-constitution"
MAX_SOURCE_BYTES = 1_000_000

SourceError = OpenBGISourceError


def fetch_source() -> str:
    request = urllib.request.Request(
        EXPORT_URL,
        headers={
            "User-Agent": "Docent-Source-Witness/2.0 (+https://github.com/PaulTiffany/docent)",
            "Accept": "text/plain,*/*;q=0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(MAX_SOURCE_BYTES + 1)
        content_type = response.headers.get("content-type", "")
    if len(payload) > MAX_SOURCE_BYTES:
        raise SourceError("source exceeds the one-megabyte safety bound")
    if not payload:
        raise SourceError("source export returned an empty body")
    text = payload.decode("utf-8-sig")
    prefix = text.lstrip()[:512].casefold()
    if "<html" in prefix or "<!doctype" in prefix:
        raise SourceError(f"source export returned HTML instead of text ({content_type!r})")
    return text


def load_source(path: Path | None) -> str:
    if path is None:
        return fetch_source()
    return path.read_text(encoding="utf-8-sig")


def manifest_text(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def snapshot_path(manifest: dict) -> Path:
    return SNAPSHOT_ROOT / version_directory(str(manifest["version_label"])) / "document.txt"


def describe_drift(expected: dict, observed: dict, *, prefix: str) -> str:
    lines = [
        prefix,
        f"expected version: {expected.get('version_label')}",
        f"observed version: {observed.get('version_label')}",
        f"expected snapshot sha256: {expected.get('snapshot_sha256')}",
        f"observed snapshot sha256: {observed.get('snapshot_sha256')}",
        f"expected constitutional-body sha256: {expected.get('normalized_document_sha256')}",
        f"observed constitutional-body sha256: {observed.get('normalized_document_sha256')}",
    ]
    expected_sections = {row["key"]: row for row in expected.get("sections", [])}
    observed_sections = {row["key"]: row for row in observed.get("sections", [])}
    changed = [
        key
        for key in sorted(expected_sections.keys() | observed_sections.keys())
        if expected_sections.get(key) != observed_sections.get(key)
    ]
    lines.append("changed sheets: " + (", ".join(changed) if changed else "none"))
    if not changed and expected.get("snapshot_sha256") != observed.get("snapshot_sha256"):
        lines.append("constitutional body is unchanged; drift is outside the compiled body")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and verify the canonical OpenBGI Constitution Google Doc."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Replace the checked source lock and versioned document snapshot with the observed source.",
    )
    parser.add_argument(
        "--from-file",
        type=Path,
        help="Use a local Google Docs text export instead of the network (testing/bootstrap only).",
    )
    args = parser.parse_args()

    try:
        observed_source = load_source(args.from_file)
        observed = build_manifest(observed_source)
    except (OSError, UnicodeError, SourceError) as exc:
        print(f"source verification failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.write:
        path = snapshot_path(observed)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonicalize(observed_source), encoding="utf-8")
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCK_PATH.write_text(manifest_text(observed), encoding="utf-8")
        print(
            "wrote source snapshot and lock "
            f"{observed['version_label']} {observed['normalized_document_sha256']}"
        )
        return

    if not LOCK_PATH.exists():
        print(
            f"source lock missing: {LOCK_PATH.relative_to(ROOT)}; bootstrap with --write",
            file=sys.stderr,
        )
        raise SystemExit(2)

    try:
        expected = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        local_path = snapshot_path(expected)
        local = build_manifest(local_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeError, SourceError) as exc:
        print(f"checked source snapshot failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if expected != local:
        print(
            describe_drift(
                expected,
                local,
                prefix="Checked OpenBGI document snapshot drifted from its lock.",
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)

    if expected != observed:
        print(
            describe_drift(
                expected,
                observed,
                prefix="Canonical OpenBGI Constitution source drifted.",
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(
        "source verified "
        f"{observed['version_label']} "
        f"{observed['normalized_document_sha256']} "
        f"({observed['cell_count']} cells)"
    )


if __name__ == "__main__":
    main()
