# Room protocol

The room API is an optional transport beside the existing `/api/chat` endpoint. It records public human messages and queues generic turn requests without invoking a model.

## Endpoints

- `GET /api/room/messages?after=<sequence>&epoch=<epoch>` returns messages later than the cursor.
- `POST /api/room/messages` appends one human message and queues one turn.
- `GET /api/room/status` returns epoch, latest sequence, connection state, busy state, and queue depth.
- `POST /api/room/reset` clears room history and queue state and advances the epoch when reset is enabled.

## Cursor and epoch semantics

Sequences increase monotonically within an epoch. Clients starting fresh use `after=0`; an epoch is optional for that initial read. A positive cursor must include the epoch that issued it. Missing epoch metadata or an earlier epoch produces `409 Conflict` with a stable error code. After reset, clients discard their cursor and begin again at zero.

History truncation does not renumber retained messages. A client whose cursor predates retained history receives every retained message later than its cursor.

## Idempotency

`idempotency_key` is optional and scoped to the current room epoch. Repeating a key returns the original message with `duplicate=true`, does not allocate another sequence, and does not queue another turn. Reset clears the idempotency index.

## Bounds and errors

Message and identifier sizes are enforced by strict Pydantic models. A full turn queue rejects new non-duplicate messages with `429 Too Many Requests`. Malformed inputs use FastAPI's deterministic `422` validation response. Room reset returns `403` unless both the setting and development/test environment permit it.

## Runtime attachment

The in-memory queue contains `TurnRequest` objects. A future runtime adapter may consume them and append validated agent messages through a mediated service, but runtime execution, WebSockets, persistent storage, and provider workers are deliberately deferred.
