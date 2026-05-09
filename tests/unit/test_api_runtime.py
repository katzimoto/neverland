from __future__ import annotations

import sqlalchemy as sa

from services.api.main import create_app
from shared.config import Settings


def test_health_route_is_public_runtime_probe() -> None:
    engine = sa.create_engine("sqlite:///:memory:")
    app = create_app(engine, Settings(auth_provider="local", jwt_secret="x" * 32))
    route = next(route for route in app.routes if route.path == "/health")

    assert route.endpoint() == {"status": "ok", "service": "api"}
