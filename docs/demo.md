# Demo checklist

The reference demo is intentionally useful without model inference. Its default collection contains the self-docent plus the verified OpenBGI Constitution for Beneficial AGI, Draft 0.6 worked example.

## Shortest path: local, no secrets

- [ ] Create and activate a virtual environment.
- [ ] Run `pip install -e ".[dev]"`.
- [ ] Run `docent-serve`.
- [ ] Open <http://localhost:7860>.
- [ ] Ask **“What is the Wisdom Clause?”**
- [ ] Confirm the answer is the exact pinned Article XI source record and provenance says deterministic / no model inference.
- [ ] Ask **“Does Docent use OmegaClaw?”** and confirm the self-docent remains part of the same reference collection.

## Verify the canonical Constitution source

The served Constitution snapshot is local and hash-pinned; normal runtime does not fetch Google Docs. Source drift is checked independently.

- [ ] Run the **Verify BGI Constitution source** workflow.
- [ ] Confirm it verifies Draft 0.6 against `sources/openbgi-constitution.lock.json`.
- [ ] Do not advance the lock automatically when the remote document changes; inspect the changed sections first.

The same verifier runs daily. It needs no secret.

## Public reference path

### GitHub / Hugging Face deployment

- [ ] Keep one narrowly scoped Hugging Face deployment token in GitHub Actions secret `HF_TOKEN`.
- [ ] Keep GitHub variable `HF_SPACE_ID=PaulTiffany/docent`.
- [ ] Run the **Synchronize Hugging Face Space** workflow.
- [ ] Set GitHub variable `DOCENT_API_BASE_URL` to the public Space origin.
- [ ] Use **GitHub Actions** as the Pages source and run **Deploy Pages demo** if needed.

The synchronizer uploads only the intended runtime files and replaces stale files in the Space repository. Space variables and secrets are separate settings and are not changed by repository synchronization.

### Hugging Face reference runtime

Use only these runtime variables for the reference Space:

```text
DOCENT_ENVIRONMENT=production
DOCENT_PROVIDER=mock
DOCENT_ALLOWED_ORIGINS=https://paultiffany.github.io
DOCENT_ROOM_RESET_ENABLED=false
```

No model credential is required. If the Space still contains an old `DOCENT_API_KEY` from the completed direct-provider experiment, remove it. Old provider-selection variables such as `DOCENT_MODEL`, `DOCENT_BASE_URL`, `DOCENT_SITE_URL`, `DOCENT_APP_TITLE`, and live-budget overrides are unnecessary for the deterministic reference deployment and may also be removed.

### Verify the Space

- [ ] Open `https://paultiffany-docent.hf.space/health`.
- [ ] Confirm `status=ok` and `provider=mock`.
- [ ] Confirm the record count includes the self-docent, OpenBGI sections, and generated development records.
- [ ] Open `/api/config/public` and confirm live inference is disabled and deterministic mode is enabled.

### Verify Pages

- [ ] Open <https://paultiffany.github.io/docent/>.
- [ ] Confirm both **Self-docent** and **OpenBGI Constitution · Draft 0.6** question groups are visible.
- [ ] Ask **“What are the anti-capture tripwires?”** and inspect the `openbgi.article-vi` source label.
- [ ] Ask **“What is the Wisdom Clause?”** and inspect the `openbgi.article-xi` source label.
- [ ] Open **Project State** and confirm incomplete runtime capabilities remain visibly incomplete.

If Pages says **Setup needed**, open **API settings** and enter the public Space origin. The browser stores only that public URL.

## Future mediated inference

The next inference path is not another browser or Space model credential. Docent should continue to authorize evidence and validate citations while a separately deployed AlphaClaw runtime provides mediated OmegaClaw inference behind a narrow provider adapter.

Until that adapter is demonstrated, the public reference deployment should remain deterministic. This preserves a useful artifact even when no inference service is available and keeps the OpenBGI evidence contract independent of any particular model provider.
