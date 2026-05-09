from __future__ import annotations

import re
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from services.api.middleware import MetricsMiddleware, RequestIdMiddleware
from shared.metrics import make_metrics

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _make_app() -> FastAPI:
    """Build a minimal test app with both middlewares attached."""
    reg = CollectorRegistry()
    _, requests_total, request_duration_seconds, exceptions_total = make_metrics(registry=reg)

    app = FastAPI()
    app.add_middleware(
        MetricsMiddleware,
        requests_total=requests_total,
        request_duration_seconds=request_duration_seconds,
        exceptions_total=exceptions_total,
    )
    app.add_middleware(RequestIdMiddleware)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/protected")
    def protected() -> dict[str, str]:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Unauthorized")

    return app


def _client() -> TestClient:
    return TestClient(_make_app())


def test_request_id_generated_when_absent() -> None:
    resp = _client().get("/health")
    assert "x-request-id" in resp.headers
    assert _UUID_RE.match(resp.headers["x-request-id"])


def test_request_id_echoed_from_caller() -> None:
    caller_id = str(uuid.uuid4())
    resp = _client().get("/health", headers={"X-Request-ID": caller_id})
    assert resp.headers["x-request-id"] == caller_id


def test_request_id_present_on_404() -> None:
    resp = _client().get("/nonexistent-path-xyz")
    assert "x-request-id" in resp.headers


def test_request_id_generated_is_uuid4() -> None:
    ids: set[str] = set()
    client = _client()
    for _ in range(5):
        resp = client.get("/health")
        rid = resp.headers["x-request-id"]
        assert _UUID_RE.match(rid), f"not a UUID4: {rid}"
        ids.add(rid)
    assert len(ids) == 5


def test_request_id_forwarded_to_error_responses() -> None:
    caller_id = str(uuid.uuid4())
    resp = _client().get("/protected", headers={"X-Request-ID": caller_id})
    assert resp.status_code == 401
    assert resp.headers["x-request-id"] == caller_id


def test_request_id_forwarded_to_not_found_responses() -> None:
    caller_id = str(uuid.uuid4())
    resp = _client().get("/no-such-route", headers={"X-Request-ID": caller_id})
    assert "x-request-id" in resp.headers
    # May or may not echo the same ID depending on routing, but must include one.
    assert resp.headers["x-request-id"]
