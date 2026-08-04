from __future__ import annotations

import argparse

import uvicorn

from docent.config import get_settings, load_contract
from docent.corpus import CorpusError, load_records


def validate_main() -> None:
    settings = get_settings()
    try:
        contract = load_contract(settings.contract_path)
        records = load_records(settings.corpus_path)
    except (CorpusError, OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Validated {len(records)} records for {contract.identity.name}.")


def serve_main() -> None:
    settings = get_settings()
    uvicorn.run("docent.app:app", host="0.0.0.0", port=7860, log_level=settings.log_level.lower())


def main() -> None:
    parser = argparse.ArgumentParser(prog="docent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    subparsers.add_parser("serve")
    args = parser.parse_args()
    if args.command == "validate":
        validate_main()
    elif args.command == "serve":
        serve_main()


if __name__ == "__main__":
    main()
