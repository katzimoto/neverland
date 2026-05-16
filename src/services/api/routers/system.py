from __future__ import annotations

from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from services.api.main import current_user
from services.api.readiness import ReadinessResponse
from services.auth.models import TokenPayload
from services.health import HealthResponse, health
from services.permissions.enforcer import require_admin

router = APIRouter(tags=["system"])


@router.get("/health")
def app_health() -> HealthResponse:
    return health("api")


@router.get("/admin/readiness", response_model=None)
def admin_readiness(
    request: Request,
    user: Annotated[TokenPayload, Depends(current_user)],
) -> ReadinessResponse:
    require_admin(user)
    readiness: ReadinessResponse = request.app.state.readiness_checker.check()
    return readiness


@router.get("/metrics")
def metrics(request: Request) -> Response:
    try:
        with request.app.state.engine.begin() as connection:
            pending = connection.execute(
                sa.text("SELECT COUNT(*) FROM dlq WHERE status = 'pending'")
            ).scalar_one_or_none()
    except sa.exc.SQLAlchemyError:
        pending = 0
    request.app.state.metrics.dlq_pending.set(float(pending or 0))
    return Response(
        content=generate_latest(request.app.state.metrics.registry),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/admin/health")
def admin_health(
    user: Annotated[TokenPayload, Depends(current_user)],
) -> dict[str, str]:
    require_admin(user)
    return {"status": "ok"}
