from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test an installed Docent wheel")
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.exists():
        raise SystemExit(f"Wheel does not exist: {wheel}")
    with tempfile.TemporaryDirectory(prefix="docent-wheel-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        run([sys.executable, "-m", "venv", str(environment)], cwd=root)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python), "-m", "pip", "install", str(wheel)], cwd=root)
        smoke = (
            "from fastapi.testclient import TestClient; "
            "from docent.app import app; "
            "r=TestClient(app).get('/health'); "
            "assert r.status_code == 200 and r.json()['status'] == 'ok'; "
            "print(r.json())"
        )
        run([str(python), "-c", smoke], cwd=root)


if __name__ == "__main__":
    main()
