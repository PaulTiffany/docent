from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

DOCUMENT_ID = "11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM"
CANONICAL_URL = f"https://docs.google.com/document/d/{DOCUMENT_ID}/edit?tab=t.0"
EXPORT_URL = f"https://docs.google.com/document/d/{DOCUMENT_ID}/export?format=txt"
EXPECTED_TITLE = "OpenBGI Constitution for Beneficial AGI"
SECTIONS = (
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
)

_ABBREVIATIONS = {
    "e.g.", "i.e.", "mr.", "mrs.", "ms.", "dr.", "prof.", "vs.", "etc.", "u.s.", "u.k.", "no."
}


class OpenBGISourceError(RuntimeError):
    """The constitutional source failed its deterministic compilation contract."""


@dataclass(frozen=True)
class OpenBGICell:
    address: str
    text: str
    sha256: str


@dataclass(frozen=True)
class OpenBGISheet:
    key: str
    heading: str
    content: str
    sha256: str
    characters: int
    cells: tuple[OpenBGICell, ...]
    cells_sha256: str


@dataclass(frozen=True)
class OpenBGIWorkbook:
    document_text: str
    version_label: str
    snapshot_sha256: str
    normalized_document_sha256: str
    sheets: tuple[OpenBGISheet, ...]

    @property
    def cell_count(self) -> int:
        return sum(len(sheet.cells) for sheet in self.sheets)


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def version_directory(version_label: str) -> str:
    match = re.fullmatch(r"Draft\s+(\d+(?:\.\d+)*)", version_label.strip())
    if match is None:
        raise OpenBGISourceError(f"unsupported Constitution version label: {version_label!r}")
    return "draft-" + match.group(1)


def _split_prose_line(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []
    if line.startswith("* "):
        return [line]

    cells: list[str] = []
    start = 0
    index = 0
    while index < len(line):
        if line[index] not in ".!?":
            index += 1
            continue
        after_punctuation = index + 1
        while after_punctuation < len(line) and line[after_punctuation] in "\"'”’)]}":
            after_punctuation += 1
        if after_punctuation >= len(line) or not line[after_punctuation].isspace():
            index += 1
            continue
        token_start = index
        while token_start > start and not line[token_start - 1].isspace():
            token_start -= 1
        if line[token_start : index + 1].casefold() in _ABBREVIATIONS:
            index += 1
            continue
        next_start = after_punctuation
        while next_start < len(line) and line[next_start].isspace():
            next_start += 1
        next_character = line[next_start] if next_start < len(line) else ""
        if next_character and not (
            next_character.isupper() or next_character.isdigit() or next_character in "\"'“‘("
        ):
            index += 1
            continue
        cells.append(line[start:after_punctuation].strip())
        start = next_start
        index = next_start
    if start < len(line):
        cells.append(line[start:].strip())
    return [cell for cell in cells if cell]


def _cellize(section_content: str) -> tuple[OpenBGICell, ...]:
    lines = canonicalize(section_content).splitlines()
    cells: list[OpenBGICell] = []
    for line in lines[1:]:
        for text in _split_prose_line(line):
            address = f"A{len(cells) + 1}"
            cells.append(OpenBGICell(address=address, text=text, sha256=sha256_text(text)))
    if not cells:
        raise OpenBGISourceError(f"constitutional sheet has no cells: {lines[0]!r}")
    return tuple(cells)


def _cells_sha256(cells: tuple[OpenBGICell, ...]) -> str:
    return sha256_text("".join(f"{cell.address}\t{cell.text}\n" for cell in cells))


def compile_sheet(key: str, heading: str, section_content: str) -> OpenBGISheet:
    content = canonicalize(section_content)
    lines = content.splitlines()
    if not lines or lines[0] != heading:
        raise OpenBGISourceError(f"constitutional sheet heading mismatch: {key}")
    cells = _cellize(content)
    return OpenBGISheet(
        key=key,
        heading=heading,
        content=content,
        sha256=sha256_text(content),
        characters=len(content),
        cells=cells,
        cells_sha256=_cells_sha256(cells),
    )


def compile_workbook(source_text: str) -> OpenBGIWorkbook:
    document_text = canonicalize(source_text)
    lines = document_text.splitlines()
    nonempty = [line for line in lines if line.strip()]
    if not nonempty or nonempty[0].strip() != EXPECTED_TITLE:
        raise OpenBGISourceError("source title does not match the canonical Constitution")
    version_label = next(
        (line.strip() for line in lines[:20] if re.fullmatch(r"Draft\s+\d+(?:\.\d+)*", line.strip())),
        None,
    )
    if version_label is None:
        raise OpenBGISourceError("source does not expose an expected Draft version label")
    positions: list[int] = []
    for _key, heading in SECTIONS:
        matches = [index for index, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            raise OpenBGISourceError(
                f"expected exactly one body heading {heading!r}; observed {len(matches)}"
            )
        positions.append(matches[0])
    if positions != sorted(positions):
        raise OpenBGISourceError("constitutional sections are not in the expected order")
    sheets: list[OpenBGISheet] = []
    normalized_sections: list[str] = []
    for index, (key, heading) in enumerate(SECTIONS):
        start = positions[index]
        end = positions[index + 1] if index + 1 < len(positions) else len(lines)
        sheet = compile_sheet(key, heading, "\n".join(lines[start:end]))
        sheets.append(sheet)
        normalized_sections.append(sheet.content.strip())
    normalized_document = "\n".join(normalized_sections) + "\n"
    return OpenBGIWorkbook(
        document_text=document_text,
        version_label=version_label,
        snapshot_sha256=sha256_text(document_text),
        normalized_document_sha256=sha256_text(normalized_document),
        sheets=tuple(sheets),
    )


def build_manifest(source_text: str) -> dict:
    workbook = compile_workbook(source_text)
    return {
        "schema_version": 2,
        "document_id": DOCUMENT_ID,
        "canonical_url": CANONICAL_URL,
        "export_url": EXPORT_URL,
        "document_title": EXPECTED_TITLE,
        "version_label": workbook.version_label,
        "snapshot_sha256": workbook.snapshot_sha256,
        "normalized_document_sha256": workbook.normalized_document_sha256,
        "section_count": len(workbook.sheets),
        "cell_count": workbook.cell_count,
        "sections": [
            {
                "key": sheet.key,
                "heading": sheet.heading,
                "sha256": sheet.sha256,
                "characters": sheet.characters,
                "cell_count": len(sheet.cells),
                "cells_sha256": sheet.cells_sha256,
            }
            for sheet in workbook.sheets
        ],
        "normalization": [
            "UTF-8 text",
            "CRLF/CR normalized to LF",
            "trailing whitespace removed",
            "runs of blank lines collapsed",
            "canonical snapshot retains document metadata and table-of-contents text",
            "constitutional body extracted by exact section headings",
        ],
        "cellization": [
            "one sheet per constitutional section",
            "prose paragraphs split at conservative sentence boundaries",
            "bullet-list items preserved as one cell",
            "cell addresses are stable A1, A2, ... within each sheet",
        ],
    }
