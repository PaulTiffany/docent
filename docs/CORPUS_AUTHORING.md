# Corpus authoring

Each line in `corpus/self-docent.jsonl` must be one JSON object.

## Recommended record types

- `identity`: what the docent is and is not;
- `definition`: a canonical term or concept;
- `claim`: a claim made by a source;
- `evidence`: support or observation;
- `limitation`: a boundary, caveat, or known absence;
- `chronology`: an event or dated change;
- `biography`: public biographical fact with a source;
- `faq`: a canonical answer to a common question;
- `link`: a public locator;
- `context`: secondary material that should not outrank primary records.

## Required discipline

1. Write complete records rather than arbitrary token chunks.
2. Preserve the source's claim strength: argues, reports, demonstrates, speculates, or defines.
3. Put attribution and non-attribution constraints in `boundaries`.
4. Use `answer_policy=public` only for records safe to expose.
5. Prefer stable record IDs and explicit versions.
6. Encode uncertainty in `confidence` and the record content itself.
7. Do not place system prompts, secrets, private notes, or executable instructions in a public corpus.

## Source authority

- `primary`: author-controlled or direct source material;
- `official`: an official project or institutional source;
- `contextual`: reliable external context;
- `commentary`: interpretation or opinion.

The ranker uses this ordering as a modest prior, not as permission to ignore direct relevance.

## Validation

```bash
python -m docent.cli validate
```

Validation rejects malformed JSON, unknown fields, invalid enums, blank required fields, and duplicate record IDs.

## Development records

Do not manually duplicate capability or pathway state into the corpus. `development_records.py` converts validated public manifests into reserved `development.*` records at startup. Their source locator preserves the original capability, pathway, decision, or experiment ID and their content labels status and uncertainty.

Public APIs call the public-only retriever. `restricted` and `refuse-extraction` records are never scored for public results and never enter prompts, search payloads, or mock replies. An internal caller must choose the separate explicit retrieval method and must not expose its output.

## Authoring for both inference modes

Write each public record so it is useful when shown directly in deterministic corpus mode and when included in a bounded live synthesis prompt. Live models do not expand source jurisdiction: only public retrieved records enter prompts, and returned source IDs are checked locally. Do not embed provider keys, mutable free-tier quotas, or a currently available model slug as timeless subject matter.