# Demo checklist

**Want real synthesis? Jump directly to [Turn on free real inference](#turn-on-free-real-inference). The local no-secret path remains the quickest smoke test.**

## Shortest path: local, no secrets

- [ ] Create and activate a virtual environment.
- [ ] Run `pip install -e ".[dev]"`.
- [ ] Run `docent-serve`.
- [ ] Open <http://localhost:7860>.
- [ ] Ask â€œWhat can this project do now?â€

Mock mode is the default. Chat, source labels, project state, and deployment guidance all work without a model key.

## Public path before adding a provider key

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

## Turn on free real inference

The provider key stays entirely in Hugging Face. Never paste it into Pages, GitHub variables, browser storage, chat, or repository files.

- [ ] Create an OpenRouter account and create a narrowly scoped API key in the OpenRouter dashboard.
- [ ] Open the Hugging Face Space **Settings** page.
- [ ] Add one Space **Secret** named `DOCENT_API_KEY` with the OpenRouter key as its value.
- [ ] Set these Space **Variables**:

```text
DOCENT_ENVIRONMENT=production
DOCENT_PROVIDER=openai_compatible
DOCENT_BASE_URL=https://openrouter.ai/api/v1
DOCENT_MODEL=openrouter/free
DOCENT_ALLOWED_ORIGINS=https://paultiffany.github.io
DOCENT_ROOM_RESET_ENABLED=false
DOCENT_SITE_URL=https://paultiffany.github.io/docent/
DOCENT_APP_TITLE=Docent
DOCENT_RATE_LIMIT_PER_HOUR=10
DOCENT_LIVE_DAILY_BUDGET=45
DOCENT_ALLOW_DETERMINISTIC_MODE=true
```

- [ ] Restart or rebuild the Space.
- [ ] Open `GET https://paultiffany-docent.hf.space/health`.
- [ ] Open `GET https://paultiffany-docent.hf.space/api/config/public`; confirm `live_inference_enabled` is true, the default mode is `live`, and no key appears.
- [ ] Open <https://paultiffany.github.io/docent/>.
- [ ] Ask: “Why does Docent represent future development pathways rather than use a conventional roadmap?”
- [ ] Confirm the response displays `live`, configured route `openrouter/free`, an actual responding model when reported, grounding, and supporting records.
- [ ] Explicitly switch to deterministic corpus mode and confirm it says “no model inference.”

To pin another model later, change only `DOCENT_MODEL` to another supported OpenRouter slug and restart the Space. A specific free model uses a currently supported `:free` slug; a paid model uses the same endpoint and server-side key. No code change is required. Model availability and limits change, so check current official OpenRouter documentation.

`openrouter/free` is a router route rather than a promise of one fixed model. Docent therefore reports the configured route and the actual response model separately.