from docent.config import Settings


def test_room_reset_is_limited_to_development_or_test() -> None:
    assert Settings(environment="development", room_reset_enabled=True).allow_room_reset is True
    assert Settings(environment="test", room_reset_enabled=True).allow_room_reset is True
    assert Settings(environment="production", room_reset_enabled=True).allow_room_reset is False
    assert Settings(environment="development", room_reset_enabled=False).allow_room_reset is False
