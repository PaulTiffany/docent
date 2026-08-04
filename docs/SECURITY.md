# Security

## Threat model

The primary risks are prompt injection inside source material, accidental disclosure, model fabrication, denial of service, and capability creep.

## Implemented controls

- records are evidence, never instructions;
- only records marked `public` enter the turn package;
- model credentials remain in the gateway environment;
- the model has no shell, filesystem, database, or arbitrary network tools;
- recent history and retrieved records are bounded;
- provider output is parsed through a strict Pydantic schema;
- record IDs not present in the retrieval set are removed;
- CORS, rate limits, request timeout, and output limits are configurable;
- public API errors do not expose provider internals.

## Production recommendations

- place the service behind TLS and an authenticated reverse proxy where appropriate;
- replace in-memory rate limiting with a shared store for multiple replicas;
- separate public and restricted corpora physically, not only by metadata;
- log source IDs and decision metadata, but avoid storing sensitive user content by default;
- pin dependency versions and scan images;
- run as a non-root user with a read-only filesystem;
- add provider quota alerts and fail closed on quota exhaustion;
- add adversarial tests for every corpus release;
- never let retrieved content change tool permissions.

## Reporting

Please open a private security advisory in the eventual GitHub repository rather than posting an exploitable issue publicly.
