from docent.config import Settings


def test_room_reset_is_limited_to_development_or_test() -> None:
    assert Settings(environment="development", room_reset_enabled=True).allow_room_reset is True
    assert Settings(environment="test", room_reset_enabled=True).allow_room_reset is True
    assert Settings(environment="production", room_reset_enabled=True).allow_room_reset is False
    assert Settings(environment="development", room_reset_enabled=False).allow_room_reset is False


def test_inference_defaults_and_opaque_model_configuration() -> None:
    mock = Settings(provider="mock", model="operator/arbitrary-model")
    assert mock.default_inference_mode == "deterministic"
    assert mock.live_inference_enabled is False

    live = Settings(
        provider="openai_compatible",
        api_key="test-only",
        base_url="https://generic-compatible.example/v1",
        model="operator/arbitrary-model:free",
    )
    assert live.default_inference_mode == "live"
    assert live.live_inference_enabled is True
    assert live.model == "operator/arbitrary-model:free"


def test_live_budget_and_app_title_are_bounded() -> None:
    assert Settings(live_daily_budget=45, app_title="Docent").live_daily_budget == 45


def test_mock_only_cannot_disable_its_only_mode() -> None:
    import pytest

    with pytest.raises(ValueError, match="must enable deterministic"):
        Settings(provider="mock", allow_deterministic_mode=False)


def test_openrouter_public_label_normalizes_operator_whitespace() -> None:
    settings = Settings(
        provider="openai_compatible",
        api_key="test-only",
        base_url=" https://openrouter.ai/api/v1/ ",
        model="openrouter/free",
    )
    assert settings.public_provider_label == "openrouter"
