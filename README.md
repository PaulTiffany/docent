# Docent

Docent is a bounded, source-grounded conversational guide. The repository is deliberately useful without model inference: its default reference collection contains a self-docent plus a worked example built from the OpenBGI Constitution for Beneficial AGI, Draft 0.6.

## See something alive

No model key is required.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
docent-serve
```

Open <http://localhost:7860>. Ask **“What is the Wisdom Clause?”** to retrieve the verified Article XI source record, or ask **“What can this project do now?”** to stay in the self-docent. The default `mock` provider returns the best matching public record deterministically and labels the response as no model inference.

Expected public client: <https://paultiffany.github.io/docent/>.

## Two reference surfaces, one evidence contract

### Self-docent

The self-docent explains the implementation, limitations, deployment, and authored development frontier from validated public records. Useful questions include:

- What is a docent?
- How is this different from unrestricted chat with a PDF?
- What remains incomplete?
- Does Docent use OmegaClaw?

### Worked example: OpenBGI Constitution

The OpenBGI worked example is not an LLM paraphrase. Docent serves exact normalized constitutional sections from a checked Draft 0.6 snapshot. Each section is bound to the canonical Google Doc ID and a SHA-256 in `sources/openbgi-constitution.lock.json`.

Useful questions include:

- What are Joy, Growth, Choice, and Continuity?
- What happens when constitutional principles conflict?
- What are the anti-capture tripwires?
- What is the Wisdom Clause?
- How should the Constitution be interpreted?

The independent **Verify BGI Constitution source** workflow fetches the canonical public Google Docs export and compares it with the checked lock every day. Source drift goes red; it does not silently rewrite the served snapshot.

## Why keep deterministic mode first-class?

The evidence boundary should survive changes in the intelligence behind it. Deterministic mode makes retrieval, source attribution, deployment, and corpus debugging inspectable with zero inference. A later runtime can synthesize across multiple authorized records without changing what counts as evidence.

The intended next mediated runtime is AlphaClaw/OmegaClaw. It is **not bundled or running in this repository yet**. Docent should continue to own evidence authorization and response validation while AlphaClaw supplies cognition behind a narrow adapter.

## Public API

- `GET /health`
- `GET /api/config/public`
- `POST /api/search`
- `POST /api/chat`
- read-only `/api/development/*`
- partial `/api/room/*`

`POST /api/chat` is the working bounded single-user path. The `/api/room` transport stores messages and queues turns but has no connected agent runtime and must not be described as a working agent room.

Public retrieval excludes `restricted` and `refuse-extraction` records before prompt or response construction.

## Inspect the project frontier

The `development/` manifests make capabilities, pathways, human decisions, and experiments part of the artifact. `GET /api/development/frontier` deterministically derives admissible and blocked pathways from declared preconditions.

“Bellman-style pressures” are qualitative authored design notes, not an optimizer. Docent computes no aggregate score and never chooses the roadmap automatically.

Validate with:

```bash
docent-validate
docent-development-validate
python tools/sync_bgi_constitution.py
```

The third command performs a network source check. Normal serving and CI tests use the local checked snapshot and need no network.

## Build another docent

A collection manifest can compose JSONL records with verified built-in source adapters. The default is `corpus/reference.collection.json`, which combines `corpus/self-docent.jsonl` with the OpenBGI snapshot. Individual JSONL corpora remain supported for simpler deployments.

See [corpus authoring](docs/CORPUS_AUTHORING.md).

## Run and deploy

- Local: `docent-serve`
- Docker: `docker build -t docent . && docker run --rm -p 7860:7860 docent`
- GitHub Pages: static client built from `web/`
- Hugging Face: Docker Space on port 7860, deterministic reference mode

Pages receives only a public Docent API URL. The Hugging Face synchronizer is manual and uses one narrowly scoped deployment token; the reference Space itself requires no model credential. See [deployment](docs/deployment.md) and the [demo checklist](docs/demo.md).

## Scope boundary

This repository contains no private token, production multi-user agent room, durable database, bundled OmegaClaw runtime, or AlphaClaw adapter. The generic provider seam remains in the implementation, but the completed direct-provider demo is no longer the reference deployment path.

Development was informed by public-agent experiments using OmegaClaw. OmegaClaw is credited in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

MIT licensed. See [LICENSE](LICENSE).
