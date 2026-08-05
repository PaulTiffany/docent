# Deployment

The same installed package runs locally, in Docker, or in a Hugging Face Docker Space. The static client is served by FastAPI or GitHub Pages.

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

Open <http://localhost:7860>. `DOCENT_PROVIDER=mock` is the default and needs no secret.

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

The image runs as unprivileged user `docent`, exposes port 7860, and health-checks `/health`. Default contract, self-corpus, development manifests, and frontend assets are both present in the image and packaged in the wheel. All in-memory state is ephemeral.

## GitHub Pages

`.github/workflows/pages.yml` builds only the canonical public assets and deploys with the supported Pages actions. Enable **Settings ? Pages ? Source: GitHub Actions** once. The workflow uses optional repository variable `DOCENT_API_BASE_URL`; no secret is required. When absent, the site displays setup guidance and accepts a local public-URL override.

Expected URL after a successful main deployment: <https://paultiffany.github.io/docent/>. This repository does not claim it is live until observed.

## Hugging Face Docker Space

Official references: [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker), [Spaces variables and secrets](https://huggingface.co/docs/hub/spaces-overview), and [`HfApi.upload_folder`](https://huggingface.co/docs/huggingface_hub/en/package_reference/hf_api).

`deploy/huggingface/README.md` supplies `sdk: docker` and `app_port: 7860`. The manual **Synchronize Hugging Face Space** workflow validates `HF_SPACE_ID`, creates or reuses the configured Space through the official Hub API, stages only intended runtime files, replaces stale remote files, and never stages the token.

GitHub Actions configuration:

- secret `HF_TOKEN`: narrowly scoped write token for the intended Space;
- variable `HF_SPACE_ID`: `owner/name`;
- optional variable `DOCENT_API_BASE_URL`: public Space origin for Pages.

Mock Space variables:

```text
DOCENT_ENVIRONMENT=production
DOCENT_PROVIDER=mock
DOCENT_ALLOWED_ORIGINS=https://paultiffany.github.io
DOCENT_ROOM_RESET_ENABLED=false
```

No model secret is required.

Model-backed Space variables:

```text
DOCENT_PROVIDER=openai_compatible
DOCENT_MODEL=<chosen model>
DOCENT_BASE_URL=<provider API base>
DOCENT_ALLOWED_ORIGINS=https://paultiffany.github.io
DOCENT_ENVIRONMENT=production
DOCENT_ROOM_RESET_ENABLED=false
```

Add Space secret `DOCENT_API_KEY=<provider credential>`. It must never appear in Pages, GitHub variables, frontend configuration, or repository files.

## Public configuration

`config.json` may contain only API base URL, repository URL, display name, and deployment mode. A browser-generated session ID is not a credential. The frontend stores only a public API URL in localStorage.

## Readiness and limitations

`GET /health` reports safe status, provider mode, record count, and Docent name. It does not reveal environment values or credentials. Room/session state disappears on sleep or restart; the epoch protocol enables resynchronization but does not recover lost messages. No deployed Space or Pages validation is claimed until live endpoints are observed.

## OpenRouter reference deployment

OpenRouter uses the generic `openai_compatible` provider; no OpenRouter-only runtime provider is required. Configure the Space secret `DOCENT_API_KEY` and the variables listed in [demo.md](demo.md#turn-on-free-real-inference). `DOCENT_MODEL` is opaque to Docent: `openrouter/free`, a currently supported `provider/model:free`, a paid route, or a model on another compatible service can be selected without a code change.

When `DOCENT_SITE_URL` and `DOCENT_APP_TITLE` are present, the provider sends the optional OpenRouter attribution headers `HTTP-Referer` and `X-OpenRouter-Title`. They contain no user message, session ID, key, path, or deployment diagnostics.

The Space key belongs only in Hugging Face Space Secrets. `HF_TOKEN` remains a GitHub Actions deployment credential and is not a model key. GitHub Pages receives only the public Docent API URL and always calls Docent, never OpenRouter.