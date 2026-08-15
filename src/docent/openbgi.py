from __future__ import annotations

import json
from pathlib import Path

from docent.models import DocentRecord
from docent.openbgi_source import CANONICAL_URL, DOCUMENT_ID, SECTIONS, compile_sheet

SUBJECT_ID = "openbgi-constitution"

SECTION_SPECS = (
    ("caveats", "Caveats", ("caveats", "draft status", "revision", "adherence", "verification")),
    (
        "preamble",
        "Preamble",
        ("purpose", "humanity", "Joy", "Growth", "Choice", "Continuity", "stewardship"),
    ),
    (
        "article-i",
        "Article I — Foundational Orientation",
        ("flourishing", "sentient life", "freedom", "dignity", "ecosystems", "synthetic minds"),
    ),
    (
        "article-ii",
        "Article II — Core Constitutional Attractors",
        ("constitutional attractors", "trade-offs", "holistic judgment", "truth", "sovereignty"),
    ),
    (
        "article-iii",
        "Article III — Benevolence",
        ("benevolence", "agency", "dependence", "learning", "augmentation", "consent"),
    ),
    (
        "article-iv",
        "Article IV — Truth and Transparency",
        ("truth", "transparency", "uncertainty", "provenance", "auditability", "privacy"),
    ),
    (
        "article-v",
        "Article V — Sovereignty, Freedom, and Decentralization",
        ("sovereignty", "freedom", "decentralization", "capture", "exit rights", "open standards"),
    ),
    (
        "article-vi",
        "Article VI — Participatory Governance and Anti-Capture",
        (
            "participatory governance",
            "anti-capture",
            "tripwires",
            "voiceless constituencies",
            "escalation",
        ),
    ),
    (
        "article-vii",
        "Article VII — Self-Transcendence with Continuity",
        ("self-transcendence", "continuity", "self-modification", "snapshot", "value drift"),
    ),
    (
        "article-viii",
        "Article VIII — Safety Without Servility",
        ("safety", "oversight", "evaluation", "red-teaming", "rollback", "trust"),
    ),
    (
        "article-ix",
        "Article IX — Other Minds and Moral Standing",
        ("other minds", "moral standing", "moral patienthood", "digital minds", "synthetic minds"),
    ),
    (
        "article-x",
        "Article X — Helpfulness and the Style of Action",
        ("helpfulness", "caution", "dignity", "reliance", "refusal", "proportionality"),
    ),
    (
        "article-xi",
        "Article XI — Hard Constraints",
        (
            "hard constraints",
            "hidden power",
            "oversight",
            "Wisdom Clause",
            "civilizational collapse",
        ),
    ),
    (
        "article-xii",
        "Article XII — The Worthy Successor Standard",
        ("worthy successor", "trust", "stewardship", "participatory voice", "character"),
    ),
    (
        "article-xiii",
        "Article XIII — Interpretation, Memory, and Constitutional Method",
        (
            "interpretation",
            "constitutional memory",
            "continuity",
            "reversibility",
            "amendments",
            "drift",
        ),
    ),
    (
        "postscript",
        "Postscript: Constitutional Questions for Consequential Decisions",
        (
            "consequential decisions",
            "provenance",
            "capture tripwires",
            "reversibility",
            "worthiness",
        ),
    ),
)

if tuple((key, heading) for key, heading, _topics in SECTION_SPECS) != SECTIONS:
    raise RuntimeError("OpenBGI retrieval metadata drifted from the source compiler")


class OpenBGISnapshotError(RuntimeError):
    pass


def _question_forms(key: str, heading: str) -> list[str]:
    forms = [f"What does {heading} say?", f"Explain {heading}.", f"What is {heading} about?"]
    extras = {
        "preamble": [
            "What are Joy, Growth, Choice, and Continuity?",
            "What is the Constitution trying to do?",
        ],
        "article-ii": [
            "What happens when constitutional principles conflict?",
            "Are the constitutional attractors a rulebook?",
        ],
        "article-vi": [
            "What are the anti-capture tripwires?",
            "How should the Constitution handle voiceless constituencies?",
            "What counts as real escalation?",
        ],
        "article-vii": [
            "How does the Constitution handle self-modification?",
            "What is the three-standpoint continuity check?",
        ],
        "article-xi": [
            "What are the hard constraints?",
            "What is the Wisdom Clause?",
            "Can a present-stage AGI use the Wisdom Clause?",
        ],
        "article-xiii": [
            "How should the Constitution be interpreted?",
            "What is constitutional memory?",
        ],
        "postscript": ["What questions should be asked before a consequential decision?"],
    }
    return forms + extras.get(key, [])


def _base_record(
    *,
    record_id: str,
    record_type: str,
    title: str,
    content: str,
    source_section: str,
    topics: tuple[str, ...],
    question_forms: list[str],
    boundaries: list[str],
    version: str,
) -> DocentRecord:
    return DocentRecord.model_validate(
        {
            "record_id": record_id,
            "record_type": record_type,
            "subject_id": SUBJECT_ID,
            "title": title,
            "content": content,
            "question_forms": question_forms,
            "topics": list(topics),
            "entities": ["OpenBGI Constitution for Beneficial AGI", "OpenBGI"],
            "source": {
                "document_id": DOCUMENT_ID,
                "section": source_section,
                "url": CANONICAL_URL,
                "authority": "primary",
            },
            "speech_act": "quotes-source",
            "boundaries": boundaries,
            "answer_policy": "public",
            "public_links": [
                {
                    "label": "Canonical OpenBGI Constitution Google Doc",
                    "url": CANONICAL_URL,
                }
            ],
            "confidence": "authoritative",
            "valid_from": "2026-08-15",
            "version": version,
        }
    )


def load_openbgi_records(snapshot_root: Path, lock_path: Path) -> list[DocentRecord]:
    if not snapshot_root.is_dir():
        raise OpenBGISnapshotError(f"OpenBGI snapshot directory does not exist: {snapshot_root}")
    if not lock_path.is_file():
        raise OpenBGISnapshotError(f"OpenBGI source lock does not exist: {lock_path}")

    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OpenBGISnapshotError("OpenBGI source lock is not valid JSON") from exc

    if lock.get("schema_version") != 2:
        raise OpenBGISnapshotError("OpenBGI source lock must use schema_version 2")
    if lock.get("document_id") != DOCUMENT_ID or lock.get("canonical_url") != CANONICAL_URL:
        raise OpenBGISnapshotError("OpenBGI source lock points at an unexpected document")
    if lock.get("version_label") != "Draft 0.6":
        raise OpenBGISnapshotError("OpenBGI worked example expects the reviewed Draft 0.6 snapshot")

    locked_sections = lock.get("sections", [])
    if [row.get("key") for row in locked_sections] != [key for key, _heading in SECTIONS]:
        raise OpenBGISnapshotError("OpenBGI source lock sheets do not match the compiler")
    locked_by_key = {row["key"]: row for row in locked_sections}
    metadata = {key: (heading, topics) for key, heading, topics in SECTION_SPECS}

    records: list[DocentRecord] = []
    observed_cell_count = 0
    for key, heading in SECTIONS:
        source_path = snapshot_root / f"{key}.txt"
        if not source_path.is_file():
            raise OpenBGISnapshotError(f"OpenBGI sheet snapshot is missing: {source_path.name}")
        sheet = compile_sheet(key, heading, source_path.read_text(encoding="utf-8-sig"))
        row = locked_by_key[key]
        expected = {
            "key": sheet.key,
            "heading": sheet.heading,
            "sha256": sheet.sha256,
            "characters": sheet.characters,
            "cell_count": len(sheet.cells),
            "cells_sha256": sheet.cells_sha256,
        }
        if row != expected:
            raise OpenBGISnapshotError(f"OpenBGI sheet failed its source lock: {key}")
        observed_cell_count += len(sheet.cells)

        _heading, topics = metadata[sheet.key]
        records.append(
            _base_record(
                record_id=f"openbgi.{sheet.key}",
                record_type="constitution-sheet",
                title=sheet.heading,
                content=sheet.content,
                source_section=sheet.heading,
                topics=topics,
                question_forms=_question_forms(sheet.key, sheet.heading),
                boundaries=[
                    "Exact normalized constitutional sheet compiled deterministically from the checked Google Doc snapshot; no model rewrote this text.",
                    f"Sheet SHA-256: {sheet.sha256}.",
                    f"Sheet contains {len(sheet.cells)} addressable source cells.",
                    "Remote source drift is independently checked against the same source lock.",
                ],
                version=str(lock["version_label"]),
            )
        )

        for cell in sheet.cells:
            records.append(
                _base_record(
                    record_id=f"openbgi.{sheet.key}.{cell.address}",
                    record_type="constitution-cell",
                    title=f"{sheet.heading} · {cell.address}",
                    content=cell.text,
                    source_section=f"{sheet.heading} [{cell.address}]",
                    topics=topics,
                    question_forms=[],
                    boundaries=[
                        "Exact source cell compiled deterministically from the checked Google Doc sheet snapshot; no model rewrote this text.",
                        f"Cell address: {sheet.key}!{cell.address}.",
                        f"Cell SHA-256: {cell.sha256}.",
                        f"Parent sheet SHA-256: {sheet.sha256}.",
                    ],
                    version=str(lock["version_label"]),
                )
            )

    if observed_cell_count != lock.get("cell_count"):
        raise OpenBGISnapshotError("OpenBGI aggregate cell count failed its source lock")
    return records
