"""Fail-closed ACL persistence and enforcement helpers for SMB documents."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.engine import Connection, RowMapping

from shared.db import db_uuid, to_uuid

ACL_SYNC_CONFIG_KEY = "acl_sync_enabled"
SMB_ACL_FEATURE_KEY = "feature.smb_acl_sync"


def normalize_windows_principal(value: str) -> str:
    """Return the canonical representation used for principal mapping keys."""
    return value.strip().upper()


class SmbAclRepository:
    """Store sanitized SMB ACL snapshots and explicit principal mappings."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def global_enabled(self) -> bool:
        """Return whether SMB ACL sync is globally enabled in runtime config."""
        value = self._connection.execute(
            sa.text("SELECT value FROM system_config WHERE key = :key"),
            {"key": SMB_ACL_FEATURE_KEY},
        ).scalar_one_or_none()
        return _config_bool(value, default=False)

    def source_enabled(self, source_id: UUID) -> bool:
        """Return whether a source is an SMB source explicitly opted into ACL sync."""
        row = (
            self._connection.execute(
                sa.text("SELECT type, config FROM ingestion_sources WHERE id = :id"),
                {"id": db_uuid(source_id)},
            )
            .mappings()
            .first()
        )
        if row is None or str(row["type"]) != "smb":
            return False
        config = _json_object(row["config"])
        return _config_bool(config.get(ACL_SYNC_CONFIG_KEY), default=False)

    def effective_enabled(self, source_id: UUID) -> bool:
        """Return whether ACL enforcement applies to a source."""
        return self.global_enabled() and self.source_enabled(source_id)

    def upsert_document_acl(
        self,
        doc_id: UUID,
        acl_data: list[dict[str, Any]] | None,
        error: str | None = None,
    ) -> None:
        """Persist a sanitized ACL snapshot or sanitized failure state for a document."""
        sanitized_error = _sanitize_error(error)
        normalized_acl = _normalize_acl_data(acl_data) if sanitized_error is None else []
        acl_hash = _acl_hash(normalized_acl) if sanitized_error is None else None
        row_id = uuid4()
        self._connection.execute(
            sa.text(
                """
                INSERT INTO document_acls (id, document_id, acl_data, acl_hash, error)
                VALUES (:id, :document_id, :acl_data, :acl_hash, :error)
                ON CONFLICT (document_id) DO UPDATE SET
                    acl_data = excluded.acl_data,
                    acl_hash = excluded.acl_hash,
                    error = excluded.error,
                    synced_at = CURRENT_TIMESTAMP
                """
            ).bindparams(sa.bindparam("acl_data", type_=sa.JSON())),
            {
                "id": db_uuid(row_id),
                "document_id": db_uuid(doc_id),
                "acl_data": normalized_acl,
                "acl_hash": acl_hash,
                "error": sanitized_error,
            },
        )

    def create_mapping(self, source_id: UUID, windows_principal: str, group_id: UUID) -> RowMapping:
        """Create or replace an explicit Windows-principal to Neverland-group mapping."""
        mapping_id = uuid4()
        normalized = normalize_windows_principal(windows_principal)
        if not normalized:
            raise ValueError("windows_principal must not be empty")
        row = (
            self._connection.execute(
                sa.text(
                    """
                    INSERT INTO smb_principal_mappings (
                        id, source_id, windows_principal, group_id
                    )
                    VALUES (:id, :source_id, :windows_principal, :group_id)
                    ON CONFLICT (source_id, windows_principal) DO UPDATE SET
                        group_id = excluded.group_id
                    RETURNING id, source_id, windows_principal, group_id, created_at
                    """
                ),
                {
                    "id": db_uuid(mapping_id),
                    "source_id": db_uuid(source_id),
                    "windows_principal": normalized,
                    "group_id": db_uuid(group_id),
                },
            )
            .mappings()
            .first()
        )
        if row is None:
            raise RuntimeError("ACL mapping insert did not persist")
        return row

    def list_mappings(self, source_id: UUID) -> list[RowMapping]:
        """List explicit Windows-principal mappings for a source."""
        rows = self._connection.execute(
            sa.text(
                """
                SELECT id, source_id, windows_principal, group_id, created_at
                FROM smb_principal_mappings
                WHERE source_id = :source_id
                ORDER BY windows_principal
                """
            ),
            {"source_id": db_uuid(source_id)},
        ).mappings()
        return list(rows)

    def delete_mapping(self, source_id: UUID, mapping_id: UUID) -> bool:
        """Delete a mapping and return whether a row was removed."""
        result = self._connection.execute(
            sa.text(
                """
                DELETE FROM smb_principal_mappings
                WHERE id = :id AND source_id = :source_id
                """
            ),
            {"id": db_uuid(mapping_id), "source_id": db_uuid(source_id)},
        )
        return result.rowcount > 0

    def can_user_access_acl(
        self, doc_id: UUID, source_id: UUID, user_group_ids: Iterable[UUID]
    ) -> bool:
        """Return True when an enabled SMB ACL snapshot allows one user group."""
        if not self.effective_enabled(source_id):
            return True

        acl_row = (
            self._connection.execute(
                sa.text("SELECT acl_data, error FROM document_acls WHERE document_id = :doc_id"),
                {"doc_id": db_uuid(doc_id)},
            )
            .mappings()
            .first()
        )
        if acl_row is None or acl_row["error"] is not None:
            return False

        acl_entries = _normalize_acl_data(_json_list(acl_row["acl_data"]))
        if not acl_entries:
            return False

        user_groups = {to_uuid(group_id) for group_id in user_group_ids}
        if not user_groups:
            return False

        principal_to_group = self._principal_group_map(source_id)
        allowed = False
        for entry in acl_entries:
            principal = normalize_windows_principal(str(entry["sid"]))
            group_id = principal_to_group.get(principal)
            if group_id is None or group_id not in user_groups:
                continue
            ace_type = entry["type"]
            if ace_type == "deny":
                return False
            if ace_type == "allow":
                allowed = True
        return allowed

    def source_ids_for_documents(self, doc_ids: Iterable[UUID]) -> dict[UUID, UUID]:
        """Batch-load source IDs for documents."""
        ids = list(doc_ids)
        if not ids:
            return {}
        rows = self._connection.execute(
            sa.text("SELECT id, source_id FROM documents WHERE id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": [db_uuid(doc_id) for doc_id in ids]},
        ).mappings()
        return {to_uuid(row["id"]): to_uuid(row["source_id"]) for row in rows}

    def filter_allowed_doc_ids(
        self, doc_ids: Iterable[UUID], user_group_ids: Iterable[UUID]
    ) -> set[UUID]:
        """Return the subset of doc IDs allowed by effective SMB ACLs."""
        source_ids = self.source_ids_for_documents(doc_ids)
        return {
            doc_id
            for doc_id, source_id in source_ids.items()
            if self.can_user_access_acl(doc_id, source_id, user_group_ids)
        }

    def _principal_group_map(self, source_id: UUID) -> dict[str, UUID]:
        rows = self._connection.execute(
            sa.text(
                """
                SELECT windows_principal, group_id
                FROM smb_principal_mappings
                WHERE source_id = :source_id
                """
            ),
            {"source_id": db_uuid(source_id)},
        ).mappings()
        return {
            normalize_windows_principal(str(row["windows_principal"])): to_uuid(row["group_id"])
            for row in rows
        }


def _config_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        parsed = json.loads(value) if value else {}
        return parsed if isinstance(parsed, dict) else {}
    return value if isinstance(value, dict) else {}


def _json_list(value: Any) -> list[dict[str, Any]]:
    parsed = (json.loads(value) if value else []) if isinstance(value, str) else value
    return parsed if isinstance(parsed, list) else []


def _normalize_acl_data(value: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if value is None:
        return []
    normalized: list[dict[str, Any]] = []
    for entry in value:
        ace_type = normalize_windows_principal(str(entry.get("type", ""))).lower()
        principal = normalize_windows_principal(str(entry.get("sid", "")))
        if ace_type not in {"allow", "deny"} or not principal:
            return []
        try:
            access_mask = int(entry.get("access_mask", 0))
        except (TypeError, ValueError):
            return []
        normalized.append({"type": ace_type, "sid": principal, "access_mask": access_mask})
    normalized.sort(key=lambda item: (item["type"], item["sid"], item["access_mask"]))
    return normalized


def _acl_hash(acl_data: list[dict[str, Any]]) -> str:
    payload = json.dumps(acl_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sanitize_error(error: str | None) -> str | None:
    if error is None:
        return None
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in error)[:64]
