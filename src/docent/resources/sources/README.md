# Canonical source witness: OpenBGI Constitution

Docent's worked Constitution example points back to the canonical Google Doc rather than treating a model transcript, JSON record set, or conversation paste as authority.

Canonical document:

- Document ID: `11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM`
- Google Doc: `https://docs.google.com/document/d/11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM/edit?tab=t.0`
- Public text export: `https://docs.google.com/document/d/11cTcfq8biFMSppDqG-P-7uIaZMSr7prfsiI5EkVZ0LM/export?format=txt`

`openbgi-constitution/draft-0.6/document.txt` is the single checked canonical text snapshot used by the runtime. `openbgi-constitution.lock.json` is only its deterministic provenance/index lock: it records the whole-document hash, the unchanged constitutional-body hash, front-matter metadata, and hashes for each compiled sheet and cell set.

Normal Docent serving never contacts Google. It compiles the checked document snapshot deterministically into:

- **Front Matter** — title, draft label, authorship/contribution/tooling/inspiration metadata;
- **Body** — Caveats, Preamble, and Articles I–XIII; and
- **Back Matter** — the Postscript.

The runtime then exposes sheet records and addressable `A1`, `A2`, ... source cells. Those records are derived views, not alternate source documents.

## Verify the live source

```bash
python tools/sync_bgi_constitution.py
```

The verifier fetches the public Google Docs text export with no model or provider key, rejects invalid source bodies, compiles the front/body/back views, and compares the live export to both the checked document snapshot and provenance lock. Source drift fails closed and reports changed sheet keys.

## Accept an intentional revision

Review the canonical change first, then run:

```bash
python tools/sync_bgi_constitution.py --write
python tools/resources.py
```

`--write` stores one versioned `document.txt`, removes legacy per-section text snapshots in that version directory, and updates the lock. Run the collection tests before accepting the revision.

## Scheduled verification

`.github/workflows/bgi-constitution-source.yml` performs the same read-only check every day and on manual dispatch. It receives no Google, model, Hugging Face, or inference secret.
