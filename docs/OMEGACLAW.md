# OmegaClaw relationship

This repository is independent, but its design was informed by public-agent experiments built on OmegaClaw-Core.

OmegaClaw's continuous agent loop, memory mechanisms, communication channels, security policy, and MeTTa/Prolog substrate demonstrated a broader agent architecture. The docent pattern deliberately narrows that architecture for a public interpretive role:

- one human message grants one possible public turn;
- retrieval is externally bounded;
- public source records are distinct from private agent memory;
- the public answer surface is a single validated response;
- tool access is absent by default;
- the docent does not initiate autonomous public action.

This initial implementation does **not** include an OmegaClaw runtime adapter because the exact transport and deployment contract should be pinned to a specific upstream release and tested against it. A later integration should live behind the `ModelProvider` protocol and preserve the same gateway validation boundary.

Upstream: <https://github.com/asi-alliance/OmegaClaw-Core>

Attribution details are in `ACKNOWLEDGMENTS.md` and `NOTICE`.
