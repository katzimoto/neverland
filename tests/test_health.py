from __future__ import annotations

from services.health import health


def test_health_response_shape() -> None:
    assert health("api") == {"status": "ok", "service": "api"}
