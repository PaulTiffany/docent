# Canonical source witness: OpenBGI Constitution

Docent's worked Constitution example points back to the canonical Google Doc rather than treating
a model transcript or copied paste as authority.

Canonical document:

- Document ID: `11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM`
- Google Doc: `https://docs.google.com/document/d/11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM/edit?tab=t.0`
- Public text export: `https://docs.google.com/document/d/11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM/export?format=txt`

`openbgi-constitution.lock.json` is deliberately metadata-only. It stores the observed draft label,
a normalized whole-document hash, and one hash per constitutional section. It does **not** copy the
Constitution into this repository.

## Verify the live source

```bash
python tools/sync_bgi_constitution.py
```

The verifier:

1. fetches the public Google Docs text export with no model and no provider key;
2. rejects HTML/login/error bodies, oversized responses, the wrong title, missing draft labels, and
   missing/reordered constitutional headings;
3. removes export-format noise deterministically;
4. hashes each article/section and the normalized constitutional body; and
5. compares those values to the checked lock.

A changed source fails closed and reports the changed section keys. The scheduled workflow never
rewrites the lock.

## Accept an intentional revision

After reviewing the canonical document itself:

```bash
python tools/sync_bgi_constitution.py --write
git diff -- sources/openbgi-constitution.lock.json
```

Committing that diff means only: *this repository has intentionally advanced its source witness to
the newly observed Constitution*. It does not certify Docent explanations as updated. Explanation
records should bind themselves to the section hash they interpret, so stale interpretations can be
detected rather than silently carried forward.

For bootstrap/testing against a saved Google Docs text export:

```bash
python tools/sync_bgi_constitution.py --from-file path/to/export.txt
```

## Scheduled verification

`.github/workflows/bgi-constitution-source.yml` performs the same read-only check every day and on
manual dispatch. It receives no Google, model, Hugging Face, or inference secret. If the document
ceases to be publicly exportable or its constitutional body changes, the workflow fails visibly.
