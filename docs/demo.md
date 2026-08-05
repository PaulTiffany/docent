# Demo checklist

## Shortest path: local, no secrets

- [ ] Create and activate a virtual environment.
- [ ] Run `pip install -e ".[dev]"`.
- [ ] Run `docent-serve`.
- [ ] Open <http://localhost:7860>.
- [ ] Ask â€œWhat can this project do now?â€

Mock mode is the default. Chat, source labels, project state, and deployment guidance all work without a model key.

## Public path: Pages plus a Hugging Face mock Space

### Paul only has to do these things

- [ ] Create a narrowly scoped Hugging Face user access token with write access to the intended Space from <https://huggingface.co/settings/tokens>.
- [ ] In GitHub repository Settings > Secrets and variables ? Actions, add secret `HF_TOKEN`.
- [ ] Add variable `HF_SPACE_ID` with `owner/name` form.
- [ ] Run the **Synchronize Hugging Face Space** workflow.
- [ ] Add or update GitHub variable `DOCENT_API_BASE_URL` to the public Space origin, for example `https://owner-name.hf.space`.
- [ ] In repository Settings > Pages, choose **GitHub Actions** as the source once.
- [ ] Run **Deploy Pages demo** (or merge to `main`, where it runs automatically).

### Verify the Space

- [ ] Open `https://<space-host>/health`; confirm `status` is `ok` and `provider` is `mock`.
- [ ] In the Space settings, use Variables for:
  - `DOCENT_ENVIRONMENT=production`
  - `DOCENT_PROVIDER=mock`
  - `DOCENT_ALLOWED_ORIGINS=https://paultiffany.github.io`
  - `DOCENT_ROOM_RESET_ENABLED=false`
- [ ] Confirm no model secret is needed.

### Verify Pages

- [ ] Open <https://paultiffany.github.io/docent/> after the Pages workflow succeeds.
- [ ] Confirm the header says **Deterministic mock mode**.
- [ ] Ask â€œWhy was the public demo selected?â€ and inspect the source record.
- [ ] Open **Project State** and confirm absent runtime capabilities remain visibly absent.

If Pages says **Setup needed**, open **API settings** and enter the public Space origin. The browser stores only that public URL. â€œUnavailableâ€ commonly means the URL is wrong, the Space is sleeping/building, `/health` is failing, or `DOCENT_ALLOWED_ORIGINS` does not include `https://paultiffany.github.io`.

## Add a real model later

Set these Hugging Face Space Variables:

- `DOCENT_PROVIDER=openai_compatible`
- `DOCENT_MODEL=<chosen model>`
- `DOCENT_BASE_URL=<provider API base>`
- `DOCENT_ALLOWED_ORIGINS=https://paultiffany.github.io`
- `DOCENT_ENVIRONMENT=production`
- `DOCENT_ROOM_RESET_ENABLED=false`

Add `DOCENT_API_KEY` only in Hugging Face Space **Secrets**. Never put it in Pages, GitHub variables, repository files, or frontend configuration.

## Live evidence discipline

Repository checks can make the pathway implementation-complete. Do not mark it demonstrated until the Pages URL, public Space `/health`, and one real browser-to-Space chat have each been observed and recorded.
