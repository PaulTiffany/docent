# Deployment

## Local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install .
uvicorn docent.app:app --host 0.0.0.0 --port 7860
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## Hugging Face Docker Space

Use the repository Dockerfile. Configure secrets in Space settings rather than committing `.env`. The health endpoint is `/health`, and the container listens on port `7860`.

## Readiness ordering

This repository runs the gateway and provider adapter in one ASGI process, avoiding a gateway/agent startup race. An external agent integration should not start until `/health` returns successfully, and its reconnect loop should use exponential backoff with a hard ceiling.

## Operational checks

- `GET /health` reports provider and record count.
- Validate the corpus in CI before deployment.
- Test one supported question, one unsupported question, one attribution boundary, and one injection attempt.
- Confirm that provider quota errors produce a generic 503 rather than retries without bound.
