from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def default_resource(relative: str) -> Path:
    """Resolve an editable-checkout resource or its installed-package copy."""
    checkout = Path(relative)
    if checkout.exists():
        return checkout
    return Path(str(files("docent").joinpath("resources", *Path(relative).parts)))


def default_resource_root() -> Path:
    checkout = Path("development")
    if checkout.exists():
        return Path(".")
    return Path(str(files("docent").joinpath("resources")))
