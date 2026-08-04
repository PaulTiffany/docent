# Corpus authoring

Each line in `corpus/records.jsonl` must be one JSON object.

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
