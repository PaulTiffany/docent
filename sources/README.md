# Canonical source witness: OpenBGI Constitution

Docent's worked Constitution example points back to the canonical Google Doc rather than treating a model transcript, conversation paste, or JSON record as authority.

Canonical document:

- Document ID: `11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM`
- Google Doc: `https://docs.google.com/document/d/11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM/edit?tab=t.0`
- Public text export: `https://docs.google.com/document/d/11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM/export?format=txt`

## Text sheets first, derived records second

`sources/openbgi-constitution/draft-0.6/*.txt` contains the checked constitutional body as one exact normalized text sheet per article/section. These sheets are deterministically extracted from the canonical Google Docs export; they are not model summaries.

`openbgi-constitution.lock.json` is **not the Constitution**. It is a provenance lock over the live export and checked text sheets: export hash, constitutional-body hash, article/section hashes, and deterministic sheet/cell hashes.

At runtime, Docent compiles those text sheets into a small source workbook:

```text
Caveats.txt      -> A1, A2, ...
Preamble.txt     -> A1, A2, ...
Article I.txt    -> A1, A2, ...
...
Article XIII.txt -> A1, A2, ...
Postscript.txt   -> A1, A2, ...
```

Each constitutional article/section is one **sheet**. Prose is conservatively sentence-split into addressable cells; Google Docs bullet-list items stay intact as one cell even when they end in semicolons. The compiler is deterministic and uses no model inference.

Docent derives two public record layers from this workbook:

- `constitution-sheet`: the exact full article/section, preserving the existing `openbgi.article-*` record IDs;
- `constitution-cell`: an exact addressable source unit such as `openbgi.article-iv.A3`.

The derived JSON/Pydantic representation is therefore an index over the source document, not a replacement for it.

## Verify the live source

```bash
python tools/sync_bgi_constitution.py
```

The verifier:

1. fetches the public Google Docs text export with no model and no provider key;
2. rejects HTML/login/error bodies, oversized responses, the wrong title, missing draft labels, and missing/reordered constitutional headings;
3. normalizes the export deterministically;
4. compiles the same sheets and cells used by Docent;
5. verifies every checked local text sheet against the lock; and
6. compares the live Google Doc against that same lock.

A changed source fails closed and reports changed sheet keys. If only document metadata or table-of-contents material changed while the constitutional body stayed fixed, the verifier says so explicitly. The scheduled workflow never rewrites the lock or snapshot.

## Accept an intentional revision

After reviewing a canonical change, this command intentionally regenerates the versioned text sheets and advances their lock:

```bash
python tools/sync_bgi_constitution.py --write
```

For bootstrap/testing against a saved Google Docs text export:

```bash
python tools/sync_bgi_constitution.py --from-file path/to/export.txt
```

A new draft should remain a new versioned snapshot rather than silently replacing an older learner-visible source. Updating the collection to a new draft is a separate reviewed action.

## Scheduled verification

`.github/workflows/bgi-constitution-source.yml` performs the same read-only check every day and on manual dispatch. It receives no Google, model, Hugging Face, or inference secret. If the document ceases to be publicly exportable or its checked source changes, the workflow fails visibly.
