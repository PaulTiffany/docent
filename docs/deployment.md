# Deployment

## Local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
make validate
make run
```

The mock provider requires no key. `/api/chat` is immediately usable. The shared room is also available but has no runtime worker in this tranche, so queued turns remain queued until reset or process restart.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The image runs as a non-root user, listens on port `7860`, and includes configuration and example corpus files. Mount deployment corpora read-only.

## Hugging Face Docker Space

Create a generic Docker Space from this repository. Keep provider credentials in Space secrets, not variables or source files. The container port is `7860`, and `/health` is the readiness endpoint. Ephemeral in-memory room/session state may disappear whenever the Space sleeps or restarts.

Set `DOCENT_ENVIRONMENT=production` in public deployments. This disables room reset even if `DOCENT_ROOM_RESET_ENABLED` is accidentally true. Configure allowed origins, history/queue bounds, timeouts, and rate limits explicitly.

## Future external runtime

A later runtime process should wait for `/health`, attach through the documented runtime/queue contracts, and reconnect with capped exponential backoff. That adapter must not receive gateway credentials or bypass retrieval and response validation. No external runtime or WebSocket channel is included now.

## Operational checks

- Run corpus validation, content audit, Ruff format/check, and pytest.
- Exercise one supported and unsupported `/api/chat` question.
- Exercise room idempotency, queue saturation, reset authorization, and stale-epoch behavior.
- Confirm provider failures remain generic `503` responses.
- Treat session and room memory as ephemeral unless durable adapters are installed.

This repository contains no subject-specific atlas or recovered deployment corpus.
