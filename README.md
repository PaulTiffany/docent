# Docent

Docent is a bounded, source-grounded conversational guide. This repository's default example is a self-docent: it explains its own implementation, limitations, deployment, and authored development frontier from validated public records.

## See something alive

No model key is required.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
docent-serve
```

Open <http://localhost:7860> and ask **“What can this project do now?”** The default `mock` provider deterministically returns the best matching public record. See the short [demo checklist](docs/demo.md).

The expected Pages URL after merge and successful deployment is <https://paultiffany.github.io/docent/>. It is not claimed live until observed.

## Ask it about itself

Useful questions include:

- What is a docent?
- How is this different from unrestricted chat with a PDF?
- What remains incomplete?
- Why was the public demo selected?
- What would a mediated runtime unlock?
- Which roadmap did the AI prove is optimal?

`POST /api/chat` remains the working bounded single-user path. The `/api/room` transport is partial: it stores messages and queues turns but has no connected agent runtime and must not be described as a working agent room.

## Inspect the project frontier

The `development/` manifests make capabilities, pathways, a human decision, and an active experiment part of the artifact. `GET /api/development/frontier` deterministically derives admissible and blocked pathways from declared preconditions.

“Bellman-style pressures” are a design metaphor: authors record immediate usefulness, cost, risk, information gain, reversibility, lock-in, and future option value with a bounded qualitative vocabulary. Docent computes no aggregate score, claims no mathematical optimum, and never selects a pathway automatically.

Validate the model with:

```bash
docent-development-validate
```

## Build another docent

Author complete `DocentRecord` objects in JSONL, adjust `config/docent.yaml`, and validate:

```bash
docent-validate
```

The default corpus is `corpus/self-docent.jsonl`. Development records are generated from authoritative manifests rather than duplicated into prose. See [corpus authoring](docs/CORPUS_AUTHORING.md).

## Run and deploy

- Local: `docent-serve`
- Docker: `docker build -t docent . && docker run --rm -p 7860:7860 docent`
- GitHub Pages: static client built from `web/`
- Hugging Face: Docker Space on port 7860; live OpenRouter inference when configured, with explicit deterministic fallback

Provider credentials stay server-side. Pages receives only a public API URL. See [deployment](docs/deployment.md).

## Public API

- `GET /health`
- `GET /api/config/public`
- `POST /api/search`
- `POST /api/chat`
- read-only `/api/development/*`
- partial `/api/room/*`

Public retrieval excludes `restricted` and `refuse-extraction` records in gateway code before prompt or response construction.

## Scope boundary

This repository contains no deleted subject-specific atlas, prior hosted-space identity, private token, conference-specific or paper-specific corpus, OmegaClaw adapter, external runtime, WebSocket agent channel, durable database, or production multi-user agent room.

Development was informed by public-agent experiments using OmegaClaw. OmegaClaw is credited in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) but is not bundled or running here.

MIT licensed. See [LICENSE](LICENSE).

## Live inference without surrendering evidence control

The reference deployment can use OpenRouter through the generic OpenAI-compatible provider. Docent still retrieves and authorizes public evidence, builds the bounded prompt, validates the response envelope, and publishes gateway-authored provenance. The operator changes models with `DOCENT_MODEL`; visitors cannot supply provider settings. Deterministic corpus mode remains available for offline use, tests, corpus debugging, and explicit fallback. See [the demo checklist](docs/demo.md#turn-on-free-real-inference).