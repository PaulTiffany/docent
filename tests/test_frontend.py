import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docent.app import app
from tools.frontend import ASSETS, OUTPUTS, SOURCE, rendered_assets, validate_public_config

ROOT = Path(__file__).parents[1]


def test_generated_frontend_outputs_match_canonical_source() -> None:
    expected = rendered_assets()
    for output in OUTPUTS:
        for name in ASSETS:
            assert (output / name).read_bytes() == expected[name]


def test_public_config_has_only_public_values_and_rejects_secret_like_data() -> None:
    config = json.loads((SOURCE / "config.json").read_text(encoding="utf-8"))
    validate_public_config(config)

    with pytest.raises(ValueError, match="keys must be exactly"):
        validate_public_config({**config, "provider_api_key": "not-a-real-value"})
    with pytest.raises(ValueError, match="Secret-like"):
        validate_public_config({**config, "api_base_url": "sk-not-a-real-secret-value"})


def test_missing_api_url_has_setup_state_and_local_override() -> None:
    script = (SOURCE / "app.js").read_text(encoding="utf-8")
    config = json.loads((SOURCE / "config.json").read_text(encoding="utf-8"))

    assert config["api_base_url"] == ""
    assert "Setup needed" in script
    assert "docent.publicApiBaseUrl" in script
    assert "localStorage" in script
    assert "API key" not in (SOURCE / "index.html").read_text(encoding="utf-8")


def test_fastapi_serves_canonical_frontend_assets() -> None:
    client = TestClient(app)

    for asset in ("/", "/app.js", "/styles.css", "/config.json"):
        response = client.get(asset)
        assert response.status_code == 200
    assert "Ask Docent about Docent" in client.get("/").text
