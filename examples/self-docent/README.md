# Self-docent example

The repository default is the complete example: Docent explains Docent from `corpus/self-docent.jsonl` plus public records generated from `development/` manifests. This directory does not carry a second corpus.

Run from the repository root:

```bash
pip install -e ".[dev]"
docent-serve
```

Open <http://localhost:7860> and use the questions in `questions.json`.

Mock mode is deterministic: it returns the top retrieved public record with a limitation explaining that no model synthesis occurred. Model-backed mode uses the same gateway, retrieval, prompt, and validated envelope, but sets `DOCENT_PROVIDER=openai_compatible` and keeps `DOCENT_API_KEY` server-side.

The browser interface in `web/` is canonical for both FastAPI and GitHub Pages. See `docs/demo.md` for the shortest deployment checklist and `docs/deployment.md` for Pages and Hugging Face details.
