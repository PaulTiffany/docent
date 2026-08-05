# Recovery evidence ledger

This ledger records behavior, not prior collection content. Historical artifacts are design evidence only and are never copied wholesale.

| Behavior or subsystem | Evidence category | Confidence | Generic interpretation | Implementation status | Related tests | Excluded subject-specific details |
|---|---|---|---|---|---|---|
| FastAPI/ASGI gateway | Current implementation | confirmed | HTTP gateway owns public contracts | implemented | `test_service`, `test_room` | Deployment identity and corpus |
| Docker and Hugging Face deployment | Current packaging and records | confirmed | One portable container on port 7860 | documented | Docker validation | Prior Space identity |
| `/health` readiness | Current implementation | confirmed | Readiness reports safe public state | implemented | service smoke coverage | Deployment-specific labels |
| Typed source records | Current implementation | confirmed | Complete validated epistemic units | implemented | `test_corpus` | Deleted corpus records |
| Bounded retrieval | Current implementation | confirmed | Gateway selects a small evidence set | implemented | `test_retrieval` | Prior collection vocabulary |
| Bounded recent transcript | Current implementation | confirmed | Session context has a hard cap | implemented | service tests | Historical conversations |
| Structured response envelope | Current implementation | confirmed | Validate reply, sources, grounding, limitations | implemented | `test_service` | Prior responses |
| Shared-room messages | Surviving workflow behavior | strongly inferred | Optional public message stream | implemented | `test_room` | Room name and event context |
| Incremental cursor polling | Surviving client behavior | confirmed | Poll messages after a sequence | implemented | cursor tests | Original client styling |
| Room epochs | Surviving client behavior | confirmed | Reset invalidates earlier cursors | implemented | reset/stale tests | Original epoch values |
| Session identifiers | Current and surviving behavior | confirmed | Client continuity is explicit metadata | implemented | HTTP room tests | Historical session values |
| Bounded queued turns | Surviving status behavior | strongly inferred | Reject work above a configured queue cap | implemented | queue-limit test | Prior capacity values |
| Agent connected/busy state | Surviving status behavior | confirmed | Finite public connection state | implemented | status-transition test | Agent identity |
| Directed mentions | Surviving client behavior | confirmed | Optional recipient metadata is preserved | implemented | directed-recipient test | Prior mention syntax/name |
| Restart recovery | Surviving client behavior | strongly inferred | New epoch tells clients to resynchronize | implemented | reset/stale tests | Prior restart messages |
| Ephemeral history | Deployment records | confirmed | Reference memory may reset with process | implemented/documented | bounded-history test | Historical messages |
| Gateway/agent separation | Architecture records | strongly inferred | Transport and runtime use narrow interfaces | contracts implemented | contract/room tests | Prior runtime implementation |
| Health-gated startup | Deployment records | strongly inferred | External runtime waits for gateway readiness | documented, adapter deferred | future integration test | Prior process topology |
| Reconnect backoff | Deployment records | strongly inferred | External adapters retry with capped exponential delay | documented, adapter deferred | future adapter test | Prior timing values |

## Confidence rules

- **confirmed**: directly present in current code or surviving public protocol behavior.
- **strongly inferred**: supported by multiple operational clues but not a complete surviving implementation.
- **tentative**: plausible but insufficiently supported; none are promoted into this tranche.
