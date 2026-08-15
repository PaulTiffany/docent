from __future__ import annotations

import hashlib
import json
from pathlib import Path

from docent.models import DocentRecord

DOCUMENT_ID = "11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM"
CANONICAL_URL = f"https://docs.google.com/document/d/{DOCUMENT_ID}/edit?tab=t.0"
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


class OpenBGISnapshotError(RuntimeError):
    pass


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


def load_openbgi_records(snapshot_root: Path, lock_path: Path) -> list[DocentRecord]:
    if not snapshot_root.is_dir():
        raise OpenBGISnapshotError(f"OpenBGI snapshot directory does not exist: {snapshot_root}")
    if not lock_path.is_file():
        raise OpenBGISnapshotError(f"OpenBGI source lock does not exist: {lock_path}")

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("document_id") != DOCUMENT_ID:
        raise OpenBGISnapshotError("OpenBGI source lock has an unexpected document ID")
    if lock.get("canonical_url") != CANONICAL_URL:
        raise OpenBGISnapshotError("OpenBGI source lock has an unexpected canonical URL")
    if lock.get("version_label") != "Draft 0.6":
        raise OpenBGISnapshotError("OpenBGI worked example expects the reviewed Draft 0.6 snapshot")

    locked_sections = {row["key"]: row for row in lock.get("sections", [])}
    expected_keys = [key for key, _heading, _topics in SECTION_SPECS]
    if list(locked_sections) != expected_keys:
        raise OpenBGISnapshotError("OpenBGI source lock sections do not match the worked example")

    records: list[DocentRecord] = []
    for key, heading, topics in SECTION_SPECS:
        source_path = snapshot_root / f"{key}.txt"
        if not source_path.is_file():
            raise OpenBGISnapshotError(f"OpenBGI snapshot section is missing: {source_path.name}")
        content = canonicalize(source_path.read_text(encoding="utf-8-sig"))
        row = locked_sections[key]
        observed_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if row.get("heading") != heading or row.get("sha256") != observed_hash:
            raise OpenBGISnapshotError(f"OpenBGI snapshot section failed its lock: {key}")
        if content.splitlines()[0] != heading:
            raise OpenBGISnapshotError(f"OpenBGI snapshot heading mismatch: {key}")

        records.append(
            DocentRecord.model_validate(
                {
                    "record_id": f"openbgi.{key}",
                    "record_type": "constitution-source",
                    "subject_id": SUBJECT_ID,
                    "title": heading,
                    "content": content,
                    "question_forms": _question_forms(key, heading),
                    "topics": list(topics),
                    "entities": ["OpenBGI Constitution for Beneficial AGI", "OpenBGI"],
                    "source": {
                        "document_id": DOCUMENT_ID,
                        "section": heading,
                        "url": CANONICAL_URL,
                        "authority": "primary",
                    },
                    "speech_act": "quotes-source",
                    "boundaries": [
                        "Exact normalized source section from the canonical Google Doc; Docent has not rewritten this text.",
                        f"Pinned Draft 0.6 section SHA-256: {observed_hash}.",
                        "Remote source drift is independently checked against the same lock.",
                    ],
                    "answer_policy": "public",
                    "public_links": [
                        {
                            "label": "Canonical OpenBGI Constitution Google Doc",
                            "url": CANONICAL_URL,
                        }
                    ],
                    "confidence": "authoritative",
                    "valid_from": "2026-08-15",
                    "version": "Draft 0.6",
                }
            )
        )
    return records
