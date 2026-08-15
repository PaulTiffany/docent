from __future__ import annotations

import json
from pathlib import Path

from docent.models import DocentRecord
from docent.openbgi_source import (
    CANONICAL_URL,
    DOCUMENT_ID,
    FRONT_MATTER_HEADING,
    FRONT_MATTER_KEY,
    SECTIONS,
    SNAPSHOT_FILENAME,
    build_manifest,
    compile_workbook,
)

SUBJECT_ID = "openbgi-constitution"

FRONT_MATTER_TOPICS = (
    "front matter",
    "authorship",
    "author",
    "contributors",
    "AI tooling",
    "inspirations",
    "version",
)

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


def _front_matter_question_forms(address: str) -> list[str]:
    return {
        "A1": [
            "What is the document called?",
            "What is the title of the OpenBGI Constitution?",
        ],
        "A2": [
            "What version is the OpenBGI Constitution?",
            "Which draft is this?",
        ],
        "A3": [
            "Who wrote the OpenBGI Constitution?",
            "Who is the initial author of the OpenBGI Constitution?",
            "Who authored the OpenBGI Constitution?",
        ],
        "A4": [
            "Who else contributed to the OpenBGI Constitution?",
            "Who made significant contributions to the OpenBGI Constitution?",
        ],
        "A5": [
            "What AI tools were used on the OpenBGI Constitution?",
            "Which AI systems were used on the OpenBGI Constitution?",
        ],
        "A6": [
            "What inspired the OpenBGI Constitution?",
            "What are the major direct inspirations for the OpenBGI Constitution?",
        ],
    }.get(address, [])


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


def _sheet_and_cell_records(
    *,
    sheet,
    topics: tuple[str, ...],
    sheet_question_forms: list[str],
    cell_question_forms,
    version: str,
) -> list[DocentRecord]:
    records = [
        _base_record(
            record_id=f"openbgi.{sheet.key}",
            record_type="constitution-sheet",
            title=sheet.heading,
            content=sheet.content,
            source_section=sheet.heading,
            topics=topics,
            question_forms=sheet_question_forms,
            boundaries=[
                "Exact normalized source sheet compiled deterministically from the checked canonical document snapshot; no model rewrote this text.",
                f"Document part: {sheet.part}.",
                f"Sheet SHA-256: {sheet.sha256}.",
                f"Sheet contains {len(sheet.cells)} addressable source cells.",
                "Remote source drift is independently checked against the same source lock.",
            ],
            version=version,
        )
    ]
    for cell in sheet.cells:
        records.append(
            _base_record(
                record_id=f"openbgi.{sheet.key}.{cell.address}",
                record_type="constitution-cell",
                title=f"{sheet.heading} · {cell.address}",
                content=cell.text,
                source_section=f"{sheet.heading} [{cell.address}]",
                topics=topics,
                question_forms=cell_question_forms(cell.address),
                boundaries=[
                    "Exact source cell compiled deterministically from the checked canonical document snapshot; no model rewrote this text.",
                    f"Document part: {sheet.part}.",
                    f"Cell address: {sheet.key}!{cell.address}.",
                    f"Cell SHA-256: {cell.sha256}.",
                    f"Parent sheet SHA-256: {sheet.sha256}.",
                ],
                version=version,
            )
        )
    return records


def load_openbgi_records(snapshot_root: Path, lock_path: Path) -> list[DocentRecord]:
    if not snapshot_root.is_dir():
        raise OpenBGISnapshotError(f"OpenBGI snapshot directory does not exist: {snapshot_root}")
    if not lock_path.is_file():
        raise OpenBGISnapshotError(f"OpenBGI source lock does not exist: {lock_path}")

    snapshot_path = snapshot_root / SNAPSHOT_FILENAME
    if not snapshot_path.is_file():
        raise OpenBGISnapshotError(f"OpenBGI document snapshot is missing: {SNAPSHOT_FILENAME}")

    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OpenBGISnapshotError("OpenBGI source lock is not valid JSON") from exc

    source_text = snapshot_path.read_text(encoding="utf-8-sig")
    manifest = build_manifest(source_text)
    if lock != manifest:
        raise OpenBGISnapshotError(
            "OpenBGI document snapshot does not exactly match its checked source lock"
        )
    if manifest.get("version_label") != "Draft 0.6":
        raise OpenBGISnapshotError("OpenBGI worked example expects the reviewed Draft 0.6 snapshot")

    workbook = compile_workbook(source_text)
    front_matter = workbook.sheets[0]
    if front_matter.key != FRONT_MATTER_KEY or front_matter.heading != FRONT_MATTER_HEADING:
        raise OpenBGISnapshotError("OpenBGI front matter failed the compiler contract")

    records = _sheet_and_cell_records(
        sheet=front_matter,
        topics=FRONT_MATTER_TOPICS,
        sheet_question_forms=[
            "What does the front matter say?",
            "Show the OpenBGI Constitution document metadata.",
        ],
        cell_question_forms=_front_matter_question_forms,
        version=workbook.version_label,
    )

    metadata = {key: (heading, topics) for key, heading, topics in SECTION_SPECS}
    for sheet in workbook.sheets[1:]:
        heading, topics = metadata[sheet.key]
        if heading != sheet.heading:
            raise OpenBGISnapshotError(f"OpenBGI sheet heading mismatch: {sheet.key}")
        records.extend(
            _sheet_and_cell_records(
                sheet=sheet,
                topics=topics,
                sheet_question_forms=_question_forms(sheet.key, sheet.heading),
                cell_question_forms=lambda _address: [],
                version=workbook.version_label,
            )
        )
    return records
