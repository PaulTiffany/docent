# Canonical source witness: OpenBGI Constitution

Docent's worked Constitution example points back to the canonical Google Doc rather than treating a model transcript or conversation paste as authority.

Canonical document:

- Document ID: `11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM`
- Google Doc: `https://docs.google.com/document/d/11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM/edit?tab=t.0`
- Public text export: `https://docs.google.com/document/d/11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM/export?format=txt`

`openbgi-constitution.lock.json` stores the reviewed Draft 0.6 label, a normalized whole-document hash, and one hash per constitutional section. `openbgi-constitution/draft-0.6/` stores those exact normalized source sections so normal Docent serving is deterministic, offline, and independent of Google Docs availability.

The local snapshot is not allowed to float independently: each served section is validated against its lock before it becomes a `DocentRecord`.

## Verify the live source

```bash
python tools/sync_bgi_constitution.py
```

The verifier:

1. fetches the public Google Docs text export with no model and no provider key;
2. rejects HTML/login/error bodies, oversized responses, the wrong title, missing draft labels, and missing/reordered constitutional headings;
3. removes export-format noise deterministically;
4. hashes each article/section and the normalized constitutional body; and
5. compares those values to the checked lock.

A changed source fails closed and reports the changed section keys. The scheduled workflow never rewrites either the lock or the served snapshot.

## Accept an intentional revision

Advancing to a new draft is deliberately more than running `--write`. Review the canonical change first, regenerate a new versioned source snapshot, update the lock, and run the collection tests. Do not silently replace Draft 0.6 files in place if their meaning has changed; preserving versioned snapshots keeps old learner traces and explanations interpretable.

For bootstrap/testing against a saved Google Docs text export:

```bash
python tools/sync_bgi_constitution.py --from-file path/to/export.txt
```

## Scheduled verification

`.github/workflows/bgi-constitution-source.yml` performs the same read-only check every day and on manual dispatch. It receives no Google, model, Hugging Face, or inference secret. If the document ceases to be publicly exportable or its constitutional body changes, the workflow fails visibly.
