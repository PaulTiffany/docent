# Docent

A bounded, source-grounded conversational guide for papers, archives, exhibitions, proceedings, projects, and other authored collections.

Docent is deliberately smaller than a general-purpose agent. It retrieves a small set of typed authoritative records, constructs a constrained turn prompt, produces one validated answer, and preserves source and author boundaries.

## Status

This repository is an initial, runnable reference implementation. It includes:

- typed JSONL source records;
- deterministic local retrieval with no vector database required;
- an OpenAI-compatible model adapter and a no-key mock adapter;
- bounded session history;
- source labels in every answer;
- a small FastAPI service and browser UI;
- corpus validation, tests, Docker packaging, and security notes.

It contains **no subject-specific material from prior docent deployments**.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
make run
```

Open <http://localhost:7860>.

The default `DOCENT_PROVIDER=mock` works without an API key. To use an OpenAI-compatible endpoint:

```bash
DOCENT_PROVIDER=openai_compatible \
DOCENT_MODEL=gpt-4.1-mini \
DOCENT_API_KEY='...' \
DOCENT_BASE_URL='https://api.openai.com/v1' \
uvicorn docent.app:app --host 0.0.0.0 --port 7860
```

## Corpus

Edit `corpus/records.jsonl`. Each line is one complete epistemic record rather than an arbitrary text chunk. Validate it with:

```bash
make validate
```

See [Corpus authoring](docs/CORPUS_AUTHORING.md).

## Design

```text
human message
  + bounded recent history
  + typed-record retrieval
  + docent contract
        |
        v
  one model call
        |
        v
  validated response envelope
        |
        v
  public answer + source labels
```

The gateway owns retrieval, prompt construction, rate limits, history bounds, and output validation. The model does not choose its own corpus or silently expand its jurisdiction.

## Shared room

The optional shared-room core records bounded public messages and queues generic turn requests without invoking a model. See [Room protocol](docs/room-protocol.md) and [Architecture](docs/architecture.md). Runtime workers and persistent stores are intentionally deferred.

## API

- `GET /health`
- `POST /api/chat`
- `POST /api/search`
- `GET /api/config/public`
- `GET /api/room/messages`
- `POST /api/room/messages`
- `GET /api/room/status`
- `POST /api/room/reset`

Example:

```bash
curl -s http://localhost:7860/api/chat \
  -H 'content-type: application/json' \
  -d '{"session_id":"demo","message":"What can this docent answer?"}' | jq
```

## OmegaClaw acknowledgment

The bounded public-agent pattern explored here was informed by experiments using [OmegaClaw-Core](https://github.com/asi-alliance/OmegaClaw-Core), a neural-symbolic agent framework created by Dr. Patrick Hammer and developed by the SingularityNET Foundation / ASI Alliance community. This repository is an independent implementation and does not bundle OmegaClaw code. See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) and [docs/OMEGACLAW.md](docs/OMEGACLAW.md).

## License

MIT. See [LICENSE](LICENSE).
