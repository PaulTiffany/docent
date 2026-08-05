# Room protocol

The room API is an optional, partial transport beside the working `POST /api/chat` endpoint. It records public human messages and queues generic turn requests; it does **not** invoke a model, connect an agent runtime, or append agent replies.

## Endpoints

- `GET /api/room/messages?after=<sequence>&epoch=<epoch>` returns messages later than the cursor.
- `POST /api/room/messages` appends one human message and queues one turn.
- `GET /api/room/status` returns epoch, latest sequence, connection state, busy state, and queue depth.
- `POST /api/room/reset` clears room and queue state and advances the epoch when protected configuration allows it.

Sequences are monotonic within an epoch. A fresh read uses `after=0`; a positive cursor must carry its issuing epoch. Missing or stale epoch metadata produces deterministic `409` errors. Reset clears history and idempotency state and creates a new epoch.

An optional idempotency key is scoped to the current epoch. Repeating it returns the original message, allocates no sequence, and queues no second turn. Directed-recipient metadata is preserved but does not cause delivery or execution.

Strict Pydantic models bound messages and identifiers. History and queued turns have independent limits. Queue saturation returns `429`; malformed input returns `422`; reset returns `403` outside development/test or when disabled.

A later mediated runtime can consume `TurnQueue`, ask the gateway to build a public `TurnRequest`, call `AgentRuntime`, validate `TurnResult`, and append exactly one agent message. That flow, WebSockets, durable storage, cross-process queues, restart recovery, and true multi-user execution are not implemented.
