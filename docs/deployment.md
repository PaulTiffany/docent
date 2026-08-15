# Deployment

The same installed package runs locally, in Docker, or in a Hugging Face Docker Space. The static client is served by FastAPI or GitHub Pages. The reference deployment is deterministic and requires no model credential.

## Local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
docent-validate
docent-development-validate
docent-serve
```

Open <http://localhost:7860>. `DOCENT_PROVIDER=mock` is the default.

## Docker

```bash
docker build -t docent .
docker run --rm -p 7860:7860 \
  -e DOCENT_ENVIRONMENT=production \
  -e DOCENT_PROVIDER=mock \
  -e DOCENT_ALLOWED_ORIGINS=https://paultiffany.github.io \
  -e DOCENT_ROOM_RESET_ENABLED=false \
  docent
```

The image runs as unprivileged user `docent`, exposes port 7860, and health-checks `/health`. Default contract, composed reference collection, verified source witnesses, development manifests, and frontend assets are present in the image and packaged in the wheel. All in-memory state is ephemeral.

## Canonical OpenBGI source witness

The reference collection contains a checked local snapshot of the OpenBGI Constitution for Beneficial AGI, Draft 0.6. Runtime serving does not depend on Google Docs availability.

`tools/sync_bgi_constitution.py` independently fetches the canonical public Google Docs text export, validates its title, version, section structure, and safety bounds, then compares whole-document and per-section hashes to `sources/openbgi-constitution.lock.json`. The scheduled **Verify BGI Constitution source** workflow runs this check daily without a secret. Source drift fails visibly; it does not rewrite the served snapshot or authored interpretation automatically.

## GitHub Pages

`.github/workflows/pages.yml` builds only the canonical public assets and deploys with supported Pages actions. Enable **Settings > Pages > Source: GitHub Actions** once. The workflow uses optional repository variable `DOCENT_API_BASE_URL`; no secret is required. When absent, the site displays setup guidance and accepts a local public-URL override.

Expected URL: <https://paultiffany.github.io/docent/>.

## Hugging Face Docker Space

`deploy/huggingface/README.md` supplies `sdk: docker` and `app_port: 7860`. The manual **Synchronize Hugging Face Space** workflow validates `HF_SPACE_ID`, stages only intended runtime files including the checked `sources/` tree, and replaces stale files in the Space repository.

GitHub Actions configuration:

- secret `HF_TOKEN`: narrowly scoped write token for the intended Space;
- variable `HF_SPACE_ID`: `PaulTiffany/docent` for the reference deployment;
- optional variable `DOCENT_API_BASE_URL`: public Space origin for Pages.

Reference Space variables:

```text
DOCENT_ENVIRONMENT=production
DOCENT_PROVIDER=mock
DOCENT_ALLOWED_ORIGINS=https://paultiffany.github.io
DOCENT_ROOM_RESET_ENABLED=false
```

No model secret is required. Space secrets and variables are not modified by the repository synchronizer. If a previous live-provider experiment left a `DOCENT_API_KEY` Space secret or model-selection variables behind, remove them for the deterministic reference deployment.

## Public configuration

`config.json` may contain only API base URL, repository URL, display name, and deployment mode. A browser-generated session ID is not a credential. The frontend stores only a public API URL in localStorage.

## Readiness and limitations

`GET /health` reports safe status, provider mode, record count, and Docent name. It does not reveal environment values or credentials. Room/session state disappears on sleep or restart; the epoch protocol enables resynchronization but does not recover lost messages.

## Future mediated inference

Docent retains a small provider seam, but the reference deployment should remain deterministic while mediated inference is developed separately. The intended next boundary is an AlphaClaw adapter: Docent authorizes and packages bounded evidence; AlphaClaw/OmegaClaw performs the inference loop; Docent validates the returned envelope and source identifiers.

That future runtime credential belongs with the runtime deployment, not in Pages and not in the OpenBGI source-verification workflow. The evidence collection remains useful and verifiable even if no inference runtime is configured.
