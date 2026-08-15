#!/usr/bin/env python3
"""Verify the canonical OpenBGI Constitution Google Doc without model mediation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "sources" / "openbgi-constitution.lock.json"

DOCUMENT_ID = "11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM"
CANONICAL_URL = f"https://docs.google.com/document/d/{DOCUMENT_ID}/edit?tab=t.0"
EXPORT_URL = f"https://docs.google.com/document/d/{DOCUMENT_ID}/export?format=txt"
EXPECTED_TITLE = "OpenBGI Constitution for Beneficial AGI"
MAX_SOURCE_BYTES = 1_000_000

SECTIONS = [
    ("caveats", "Caveats"),
    ("preamble", "Preamble"),
    ("article-i", "Article I — Foundational Orientation"),
    ("article-ii", "Article II — Core Constitutional Attractors"),
    ("article-iii", "Article III — Benevolence"),
    ("article-iv", "Article IV — Truth and Transparency"),
    ("article-v", "Article V — Sovereignty, Freedom, and Decentralization"),
    ("article-vi", "Article VI — Participatory Governance and Anti-Capture"),
    ("article-vii", "Article VII — Self-Transcendence with Continuity"),
    ("article-viii", "Article VIII — Safety Without Servility"),
    ("article-ix", "Article IX — Other Minds and Moral Standing"),
    ("article-x", "Article X — Helpfulness and the Style of Action"),
    ("article-xi", "Article XI — Hard Constraints"),
    ("article-xii", "Article XII — The Worthy Successor Standard"),
    ("article-xiii", "Article XIII — Interpretation, Memory, and Constitutional Method"),
    ("postscript", "Postscript: Constitutional Questions for Consequential Decisions"),
]


class SourceError(RuntimeError):
    """The remote source failed the provenance contract."""


def canonicalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    output: list[str] = []
    previous_blank = False
    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        if not line:
            if not previous_blank:
                output.append("")
            previous_blank = True
            continue
        output.append(line)
        previous_blank = False
    return "\n".join(output).strip() + "\n"


def fetch_source() -> str:
    request = urllib.request.Request(
        EXPORT_URL,
        headers={
            "User-Agent": "Docent-Source-Witness/1.0 (+https://github.com/PaulTiffany/docent)",
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


def build_manifest(source_text: str) -> dict:
    text = canonicalize(source_text)
    lines = text.splitlines()
    nonempty = [line for line in lines if line.strip()]
    if not nonempty or nonempty[0].strip() != EXPECTED_TITLE:
        raise SourceError("source title does not match the canonical Constitution")
    version_label = next(
        (
            line.strip()
            for line in lines[:20]
            if re.fullmatch(r"Draft\s+\d+(?:\.\d+)*", line.strip())
        ),
        None,
    )
    if version_label is None:
        raise SourceError("source does not expose an expected Draft version label")

    positions: list[int] = []
    for _key, heading in SECTIONS:
        matches = [index for index, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            raise SourceError(
                f"expected exactly one body heading {heading!r}; observed {len(matches)}"
            )
        positions.append(matches[0])
    if positions != sorted(positions):
        raise SourceError("constitutional sections are not in the expected order")

    section_rows: list[dict] = []
    normalized_sections: list[str] = []
    for index, (key, heading) in enumerate(SECTIONS):
        start = positions[index]
        end = positions[index + 1] if index + 1 < len(positions) else len(lines)
        normalized = canonicalize("\n".join(lines[start:end]))
        normalized_sections.append(normalized.strip())
        section_rows.append(
            {
                "key": key,
                "heading": heading,
                "sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                "characters": len(normalized),
            }
        )

    normalized_document = "\n".join(normalized_sections) + "\n"
    return {
        "schema_version": 1,
        "document_id": DOCUMENT_ID,
        "canonical_url": CANONICAL_URL,
        "export_url": EXPORT_URL,
        "document_title": EXPECTED_TITLE,
        "version_label": version_label,
        "normalized_document_sha256": hashlib.sha256(
            normalized_document.encode("utf-8")
        ).hexdigest(),
        "section_count": len(section_rows),
        "sections": section_rows,
        "normalization": [
            "UTF-8 text",
            "CRLF/CR normalized to LF",
            "trailing whitespace removed",
            "runs of blank lines collapsed",
            "table-of-contents material excluded by exact section-heading extraction",
        ],
    }


def manifest_text(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def describe_drift(expected: dict, observed: dict) -> str:
    lines = [
        "Canonical OpenBGI Constitution source drifted.",
        f"expected version: {expected.get('version_label')}",
        f"observed version: {observed.get('version_label')}",
        f"expected document sha256: {expected.get('normalized_document_sha256')}",
        f"observed document sha256: {observed.get('normalized_document_sha256')}",
    ]
    expected_sections = {row["key"]: row for row in expected.get("sections", [])}
    observed_sections = {row["key"]: row for row in observed.get("sections", [])}
    changed = [
        key
        for key in sorted(expected_sections.keys() | observed_sections.keys())
        if expected_sections.get(key) != observed_sections.get(key)
    ]
    lines.append("changed sections: " + (", ".join(changed) if changed else "none"))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and verify the canonical OpenBGI Constitution Google Doc."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Replace the checked provenance lock with the observed source manifest.",
    )
    parser.add_argument(
        "--from-file",
        type=Path,
        help="Use a local Google Docs text export instead of the network (testing/bootstrap only).",
    )
    args = parser.parse_args()

    try:
        observed = build_manifest(load_source(args.from_file))
    except (OSError, UnicodeError, SourceError) as exc:
        print(f"source verification failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.write:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCK_PATH.write_text(manifest_text(observed), encoding="utf-8")
        print(
            "wrote source lock "
            f"{observed['version_label']} {observed['normalized_document_sha256']}"
        )
        return

    if not LOCK_PATH.exists():
        print(
            f"source lock missing: {LOCK_PATH.relative_to(ROOT)}; bootstrap with --write",
            file=sys.stderr,
        )
        raise SystemExit(2)
    expected = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if expected != observed:
        print(describe_drift(expected, observed), file=sys.stderr)
        raise SystemExit(1)
    print(f"source verified {observed['version_label']} {observed['normalized_document_sha256']}")


if __name__ == "__main__":
    main()
