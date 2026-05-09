"""ASGI entrypoint for container and production-style runtime."""

from __future__ import annotations

import sqlalchemy as sa

from services.api.main import create_app
from shared.config import get_settings

settings = get_settings()
engine = sa.create_engine(settings.postgres_url, pool_pre_ping=True)
app = create_app(engine, settings)
