from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "web"
OUTPUTS = (ROOT / "src" / "docent" / "static", ROOT / "docs")
ASSETS = ("index.html", "styles.css", "app.js", "config.json")
SECRET_FRAGMENTS = ("secret", "token", "password", "credential", "api_key", "apikey")


def public_config(api_base_url: str | None = None) -> dict[str, str]:
    config = json.loads((SOURCE / "config.json").read_text(encoding="utf-8"))
    if api_base_url is not None:
        config["api_base_url"] = api_base_url.rstrip("/")
        config["deployment_mode"] = "github-pages"
    validate_public_config(config)
    return config


def validate_public_config(config: dict) -> None:
    allowed = {"api_base_url", "repository_url", "display_name", "deployment_mode"}
    if set(config) != allowed:
        raise ValueError(f"Public config keys must be exactly: {', '.join(sorted(allowed))}")
    serialized = json.dumps(config).casefold()
    for fragment in SECRET_FRAGMENTS:
        if fragment in serialized:
            raise ValueError(f"Secret-like fragment is forbidden in public config: {fragment}")
    for key, value in config.items():
        if not isinstance(value, str):
            raise TypeError(f"Public config value {key} must be a string")
        if "hf_" in value.casefold() or "sk-" in value.casefold():
            raise ValueError(f"Secret-like value is forbidden in public config: {key}")


def rendered_assets(api_base_url: str | None = None) -> dict[str, bytes]:
    config = json.dumps(public_config(api_base_url), indent=2, ensure_ascii=False) + "\n"
    return {
        name: (config.encode() if name == "config.json" else (SOURCE / name).read_bytes())
        for name in ASSETS
    }


def synchronize(*, check: bool, api_base_url: str | None) -> list[str]:
    expected = rendered_assets(api_base_url)
    drift: list[str] = []
    for output in OUTPUTS:
        output.mkdir(parents=True, exist_ok=True)
        for name, content in expected.items():
            target = output / name
            if check:
                if not target.exists() or target.read_bytes() != content:
                    drift.append(target.relative_to(ROOT).as_posix())
            else:
                target.write_bytes(content)
    return drift


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or verify canonical Docent frontend assets")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--api-base-url")
    parser.add_argument("--output", type=Path, help="Optional Pages artifact directory")
    args = parser.parse_args()

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        for name, content in rendered_assets(args.api_base_url).items():
            (args.output / name).write_bytes(content)
        return

    drift = synchronize(check=args.check, api_base_url=args.api_base_url)
    if drift:
        print("Generated frontend assets have drifted:\n" + "\n".join(drift), file=sys.stderr)
        raise SystemExit(1)
    if not args.check:
        print("Synchronized canonical frontend into FastAPI and Pages outputs.")


if __name__ == "__main__":
    main()
