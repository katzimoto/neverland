from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from services.api.main import create_app
from services.api.observability import install_enhanced_request_observability
from shared.config import Settings


def test_enhanced_observability_logs_unhandled_errors() -> None:
    engine = sa.create_engine("sqlite:///:memory:")
    app = create_app(engine, Settings(app_env="test", auth_provider="local"))
    install_enhanced_request_observability(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    client = TestClient(app)

    with patch("services.api.observability.logger") as mock_logger:
        response = client.get("/boom", headers={"X-Request-ID": "connector-debug"})

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "connector-debug"
    mock_logger.exception.assert_called_once()
    call_args = mock_logger.exception.call_args
    message = call_args[0][0]
    assert "Unhandled API request error" in message
    assert "request_id=connector-debug" in message
    assert "method=GET" in message
    assert "path=/boom" in message
    assert "error_type=RuntimeError" in message
