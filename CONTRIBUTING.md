# Contributing

Contributions are welcome through focused issues and pull requests.

Before submitting:

```bash
pip install -e '.[dev]'
make validate
make lint
make test
```

Corpus changes should include tests for expected retrieval and at least one boundary case. Architectural changes should preserve the central invariant: retrieval and capability policy remain outside the model's discretionary control.
