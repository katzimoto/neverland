from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.engine import Connection

from services.auth.models import TokenPayload, UserIdentity
from services.auth.repository import AuthRepository
from services.permissions.acl_repository import SmbAclRepository
from shared.metrics import current_metrics


def require_admin(user: TokenPayload | UserIdentity) -> None:
    """Raise 403 unless the user has admin privileges."""
    if not user.is_admin:
        metrics = current_metrics()
        if metrics is not None:
            metrics.authz_denials_total.labels("admin", "access").inc()
        raise HTTPException(status_code=403, detail="Admin privileges required")


def get_allowed_groups(user: TokenPayload | UserIdentity) -> list[UUID]:
    """Return the group IDs carried by the authenticated user context."""
    return list(user.groups)


def assert_source_access(
    source_id: UUID, user: TokenPayload | UserIdentity, repository: AuthRepository
) -> None:
    """Raise 403 unless the user can access a source through source grants."""
    if not repository.user_can_access_source(user, source_id):  # type: ignore[arg-type]
        metrics = current_metrics()
        if metrics is not None:
            metrics.authz_denials_total.labels("source", "read").inc()
        raise HTTPException(status_code=403, detail="Source access denied")


def assert_doc_access(
    doc_id: UUID, user: TokenPayload | UserIdentity, repository: AuthRepository
) -> None:
    """Raise 403 unless the user can access the document's source."""
    source_id = repository.document_source_id(doc_id)
    if source_id is None:
        raise HTTPException(status_code=404, detail="Document not found")
    assert_source_access(source_id, user, repository)


def check_doc_acl_access(
    doc_id: UUID,
    source_id: UUID,
    user: TokenPayload | UserIdentity,
    connection: Connection,
) -> bool:
    """Return whether an enabled SMB ACL snapshot allows this document.

    ACL checks are additive: this helper never grants source access by itself.
    Callers must run ``assert_doc_access`` first and then apply this helper as a
    fail-closed restriction layer for opted-in SMB sources.
    """
    return SmbAclRepository(connection).can_user_access_acl(doc_id, source_id, user.groups)


def assert_doc_acl_access(
    doc_id: UUID,
    source_id: UUID,
    user: TokenPayload | UserIdentity,
    connection: Connection,
) -> None:
    """Raise 403 when enabled SMB ACLs deny or cannot validate document access."""
    if not check_doc_acl_access(doc_id, source_id, user, connection):
        metrics = current_metrics()
        if metrics is not None:
            metrics.authz_denials_total.labels("document_acl", "read").inc()
        raise HTTPException(status_code=403, detail="Document access denied")
