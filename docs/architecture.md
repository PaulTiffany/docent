# Architecture

Docent is a bounded public interpreter. The gateway, not the model, owns retrieval, capability policy, validation, and publication.

## Two entry paths

The bounded single-user path remains `POST /api/chat`: one message, bounded session history, typed-record retrieval, one provider call, and one validated response envelope.

The optional shared-room path under `/api/room` accepts and stores human messages, exposes cursor-based polling and room status, and places bounded `TurnRequest` objects on an in-memory queue. It does not call a provider. This keeps public transport state separate from agent execution.

## Components

- `corpus.py` validates complete typed records.
- `retrieval.py` provides deterministic bounded lexical retrieval.
- `prompting.py` separates instructions, transcript, and evidence.
- `service.py` orchestrates the existing single-user turn.
- `contracts.py` defines replaceable room, queue, runtime, and session interfaces.
- `room.py` supplies bounded in-memory room and queue implementations.
- `providers/` isolates model-provider calls used by `/api/chat`.
- `app.py` exposes HTTP contracts and maps domain failures to explicit status codes.
- `content_audit.py` guards generic implementation surfaces against configured deployment identifiers.

## Runtime boundary

`AgentRuntime` receives a `TurnRequest` containing the triggering message, bounded context, retrieved records, and explicit session/room metadata. It returns a `TurnResult` containing a validated public envelope and operational timing/status metadata. Neither contract contains unrestricted internal reasoning.

A future external runtime attaches by implementing `AgentRuntime` and consuming `TurnQueue`; it must not move retrieval or output validation behind the runtime boundary. No external-agent adapter is included yet.

## Persistence and bounds

The reference stores are intentionally in-memory. Room history and queued turns have independent configurable bounds. Restarting the process loses room history; resetting a room creates a new epoch and invalidates old cursors. Durable adapters can implement the same protocols later.

No subject-specific atlas or prior deployment corpus is included.
