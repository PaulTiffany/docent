# Architecture

## Principle

A docent is a bounded public interpreter, not an unconstrained assistant with a pile of documents.

The trust boundary lives in the gateway:

1. The human supplies one message.
2. The gateway obtains a bounded recent transcript.
3. Retrieval selects a small number of complete public records.
4. The gateway constructs the model prompt from a fixed contract and retrieved evidence.
5. One provider call returns a JSON envelope.
6. The gateway validates the envelope and removes invented record identifiers.
7. The service publishes exactly one answer.

## Components

- `corpus.py`: validates JSONL typed records.
- `retrieval.py`: deterministic BM25-style local retrieval with authority and confidence weights.
- `prompting.py`: separates system contract, transcript, and evidence.
- `providers/`: model-provider boundary.
- `service.py`: turn orchestrator and response validator.
- `history.py`: bounded per-session transcript.
- `rate_limit.py`: simple deployment guardrail.
- `app.py`: HTTP API and static UI.

## Why complete records

A record is authored as an epistemic unit. It includes content, source role, confidence, boundaries, and answer policy. Retrieval returns the complete record instead of re-chunking it at query time. This makes source authority and limitations available to the model alongside the claim.

## Current retrieval

The first release uses a deterministic lexical ranker so the repository works with no model downloads, database, or network connection. The retrieval interface is intentionally small; a hybrid vector implementation can replace it without changing the gateway contract.

## Model boundary

The model receives no API keys and no direct file, shell, database, or network tools. It receives only the turn package and returns one JSON object. Any future tool must be explicitly allowlisted and mediated by the gateway.

## Persistence

The reference service keeps session history in memory. Production deployments should use a durable store if continuity across process restarts is required. Corpus records should remain versioned source artifacts, not conversational memory.
