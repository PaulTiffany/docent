# Development state

`development/` is the authoritative, machine-readable description of how Docent can develop.

- `capabilities.yaml` records present, partial, experimental, absent, and deprecated abilities with evidence and limitations.
- `pathways/` records possible changes, preconditions, consequences, authored qualitative pressures, and completion evidence.
- `decisions/` records explicit human selection among pathways.
- `experiments/` records hypotheses, observations, safety boundaries, and honest result status.

The frontier is deterministic over these manifests and read-only. Bellman-style pressure profiles expose user value, information gain, cost, risk, reversibility, lock-in, and future option value as authored `low`, `medium`, `high`, or `unknown` descriptions. They are a metaphor and design structure, not a mathematical value function. No aggregate score or “optimal path” is produced.

Run `docent-development-validate`. The validator rejects duplicate identifiers, unsafe or broken references, inconsistent pathway statuses, missing dependencies, and capability dependency cycles.

At startup, public records are generated in the reserved `development.*` namespace. They preserve original manifest IDs, status, uncertainty, and evidence state. Proposed work is never presented as implemented, and an active experiment is never presented as successful.
