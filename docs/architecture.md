# Architecture

Docent is a bounded public interpreter and a self-describing research artifact. The gateway—not a provider or browser—owns public retrieval, capability policy, history bounds, validation, and publication.

## Working single-user path

```text
POST /api/chat
  ? strict ChatRequest and rate limit
  ? bounded SessionHistory
  ? LexicalRetriever.search (public records only)
  ? fixed contract + transcript + evidence prompt
  ? configured ModelProvider
  ? strict DocentEnvelope validation
  ? unique retrieved source IDs + ChatResponse
```

`DocentService` preserves this existing path. Restricted and refuse-extraction records are filtered before scoring, prompt construction, `/api/search`, or mock output. An explicitly named `search_internal` seam exists for a future trusted policy, but no public endpoint calls it.

## Self-describing development state

`development.py` validates `CapabilityRecord`, `PathwayRecord`, `DecisionRecord`, and `ExperimentRecord` manifests and derives `DevelopmentFrontier`. The frontier reports current capabilities, admissible pathways, blocked pathways with unmet preconditions, unlocks, and authored qualitative pressures. It never mutates a manifest or selects an optimum.

`development_records.py` converts public manifests to reserved `development.*` `DocentRecord` evidence at load time. The original manifest ID remains in the source locator. This makes status and uncertainty retrievable without maintaining a second prose copy.

Read-only endpoints under `/api/development` expose stable, ordered models. There are no query-driven mutations or write endpoints.

## Canonical frontend

`web/` is the only authored frontend source. `tools/frontend.py` deterministically builds identical FastAPI assets under `src/docent/static/` and Pages assets under `docs/`. CI rejects drift and secret-like public configuration. The client calls same-origin APIs under FastAPI or a configured public origin under Pages; it never calls a model provider directly.

## Partial room transport

The optional `/api/room` path stores human messages, exposes cursor/epoch polling and status, and places bounded `TurnRequest` values on an in-memory queue. It does not call a provider or append agent replies. `AgentRuntime` remains an unimplemented protocol seam. This honest separation prevents the transport from masquerading as a working agent room.

## Provider and runtime boundaries

`ModelProvider` is used only by the single-user service. `MockProvider` is deterministic and keyless; `OpenAICompatibleProvider` is server-side and timeout-bounded. Provider output cannot expand the retrieved source jurisdiction.

A future mediated runtime should preserve this flow:

```text
human RoomMessage ? bounded queue ? gateway-built TurnRequest
? gateway-controlled public retrieval ? AgentRuntime
? validated TurnResult ? exactly one agent RoomMessage
```

External transports, OmegaClaw adapters, durable persistence, WebSockets, and true multi-user orchestration remain deliberately absent.

## Persistence and packaging

Session, room, queue, and idempotency state are in-process and ephemeral. Reset creates a new epoch; process restart loses state. Packaged defaults under `docent.resources` allow an installed wheel to resolve the contract, self-corpus, development manifests, and static assets outside the repository root. Environment path overrides remain supported.

No subject-specific atlas is included.
