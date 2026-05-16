from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from services.api.main import current_user
from services.auth.jwt import JwtService
from services.auth.models import (
    LoginRequest,
    LoginResponse,
    SignUpRequest,
    TokenPayload,
    UserResponse,
)
from services.auth.repository import AuthRepository
from services.auth.service import AuthService

router = APIRouter(tags=["auth"])


@contextmanager
def _repository_context(request: Request) -> Iterator[AuthRepository]:
    with request.app.state.engine.begin() as connection:
        yield AuthRepository(connection)


def _jwt_service(request: Request) -> JwtService:
    return JwtService(secret=request.app.state.settings.jwt_secret)


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request) -> LoginResponse:
    with _repository_context(request) as repository:
        service = AuthService(
            repository=repository,
            jwt_service=_jwt_service(request),
            auth_provider=request.app.state.settings.auth_provider,
            ldap_authenticator=request.app.state.ldap_authenticator,
            metrics=request.app.state.metrics,
        )
        return service.authenticate(body.email, body.password)


@router.post("/auth/signup", response_model=LoginResponse)
def signup(body: SignUpRequest, request: Request) -> LoginResponse:
    with _repository_context(request) as repository:
        service = AuthService(
            repository=repository,
            jwt_service=_jwt_service(request),
            auth_provider=request.app.state.settings.auth_provider,
            ldap_authenticator=request.app.state.ldap_authenticator,
            metrics=request.app.state.metrics,
        )
        return service.register(body.email, body.password, body.display_name)


@router.post("/auth/logout")
def logout(_: Annotated[TokenPayload, Depends(current_user)]) -> dict[str, bool]:
    return {"ok": True}


@router.get("/auth/me", response_model=UserResponse)
def me(user: Annotated[TokenPayload, Depends(current_user)]) -> UserResponse:
    return UserResponse.from_token(user)
