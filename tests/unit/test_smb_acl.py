from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from services.api.main import create_app
from services.auth.passwords import hash_password
from services.auth.repository import AuthRepository
from services.documents.repository import DocumentRepository
from services.permissions.acl_repository import SmbAclRepository
from services.permissions.enforcer import assert_doc_access, check_doc_acl_access
from services.search.hybrid import SearchResult
from shared.config import Settings
from shared.db import db_uuid

TEST_JWT_SECRET = "x" * 32
SID_ALLOW = "S-1-5-21-1-2-3-1001"
SID_DENY = "S-1-5-21-1-2-3-2001"


def _enable_global(connection: sa.Connection, enabled: bool = True) -> None:
    connection.execute(
        sa.text(
            "UPDATE system_config SET value = :value WHERE key = 'feature.smb_acl_sync'"
        ).bindparams(sa.bindparam("value", type_=sa.JSON())),
        {"value": enabled},
    )


def _setup_acl_doc(
    engine: Engine,
    *,
    global_enabled: bool = True,
    source_enabled: bool = True,
    grant_source: bool = True,
    acl_data: list[dict[str, object]] | None = None,
    acl_error: str | None = None,
) -> tuple[UUID, UUID, object]:
    with engine.begin() as connection:
        _enable_global(connection, global_enabled)
        auth_repo = AuthRepository(connection)
        user = auth_repo.create_local_user(
            email="user@example.com",
            password_hash=hash_password("secret"),
            display_name="User",
            group_names=["legal"],
        )
        group_id = user.groups[0]
        source_id = auth_repo.create_ingestion_source("SMB Source", source_type="smb")
        connection.execute(
            sa.text("UPDATE ingestion_sources SET config = :config WHERE id = :id").bindparams(
                sa.bindparam("config", type_=sa.JSON())
            ),
            {"id": db_uuid(source_id), "config": {"acl_sync_enabled": source_enabled}},
        )
        if grant_source:
            auth_repo.grant_source_to_group(source_id, group_id)
        doc_repo = DocumentRepository(connection)
        doc = doc_repo.create(
            source_id=source_id,
            external_id="smb://fileserver/share/doc.txt",
            source="smb",
            mime_type="text/plain",
            title="ACL Doc",
            path="/data/doc.txt",
        )
        assert doc is not None
        acl_repo = SmbAclRepository(connection)
        acl_repo.create_mapping(source_id, SID_ALLOW, group_id)
        acl_repo.create_mapping(source_id, "CORP\\LEGAL_TEAM", group_id)
        if acl_data is not None or acl_error is not None:
            acl_repo.upsert_document_acl(doc.id, acl_data, error=acl_error)
        return source_id, doc.id, user


def test_acl_disabled_globally_skips_check(migrated_engine: Engine) -> None:
    source_id, doc_id, user = _setup_acl_doc(
        migrated_engine,
        global_enabled=False,
        source_enabled=True,
        acl_error="acl_read_failed",
    )
    with migrated_engine.begin() as connection:
        assert check_doc_acl_access(doc_id, source_id, user, connection) is True


def test_acl_disabled_per_source_skips_check(migrated_engine: Engine) -> None:
    source_id, doc_id, user = _setup_acl_doc(
        migrated_engine,
        global_enabled=True,
        source_enabled=False,
        acl_error="acl_read_failed",
    )
    with migrated_engine.begin() as connection:
        assert check_doc_acl_access(doc_id, source_id, user, connection) is True


def test_acl_allow_ace_mapped_group_grants_access(migrated_engine: Engine) -> None:
    source_id, doc_id, user = _setup_acl_doc(
        migrated_engine,
        acl_data=[{"type": "allow", "sid": SID_ALLOW, "access_mask": 1}],
    )
    with migrated_engine.begin() as connection:
        assert check_doc_acl_access(doc_id, source_id, user, connection) is True


def test_acl_deny_ace_overrides_allow(migrated_engine: Engine) -> None:
    source_id, doc_id, user = _setup_acl_doc(
        migrated_engine,
        acl_data=[
            {"type": "allow", "sid": SID_ALLOW, "access_mask": 1},
            {"type": "deny", "sid": SID_ALLOW, "access_mask": 1},
        ],
    )
    with migrated_engine.begin() as connection:
        assert check_doc_acl_access(doc_id, source_id, user, connection) is False


def test_unknown_sid_and_empty_acl_fail_closed(migrated_engine: Engine) -> None:
    source_id, doc_id, user = _setup_acl_doc(
        migrated_engine,
        acl_data=[{"type": "allow", "sid": SID_DENY, "access_mask": 1}],
    )
    with migrated_engine.begin() as connection:
        assert check_doc_acl_access(doc_id, source_id, user, connection) is False
        SmbAclRepository(connection).upsert_document_acl(doc_id, [])
        assert check_doc_acl_access(doc_id, source_id, user, connection) is False


def test_acl_read_error_and_missing_acl_fail_closed(migrated_engine: Engine) -> None:
    source_id, doc_id, user = _setup_acl_doc(migrated_engine, acl_error="acl_read_failed")
    with migrated_engine.begin() as connection:
        assert check_doc_acl_access(doc_id, source_id, user, connection) is False
        connection.execute(
            sa.text("DELETE FROM document_acls WHERE document_id = :id"),
            {"id": db_uuid(doc_id)},
        )
        assert check_doc_acl_access(doc_id, source_id, user, connection) is False


def test_domain_principal_mapping_match(migrated_engine: Engine) -> None:
    source_id, doc_id, user = _setup_acl_doc(
        migrated_engine,
        acl_data=[{"type": "allow", "sid": "corp\\legal_team", "access_mask": 1}],
    )
    with migrated_engine.begin() as connection:
        assert check_doc_acl_access(doc_id, source_id, user, connection) is True


def test_source_level_required_regardless_of_acl(migrated_engine: Engine) -> None:
    _, doc_id, user = _setup_acl_doc(
        migrated_engine,
        grant_source=False,
        acl_data=[{"type": "allow", "sid": SID_ALLOW, "access_mask": 1}],
    )
    with migrated_engine.begin() as connection:
        auth_repo = AuthRepository(connection)
        try:
            assert_doc_access(doc_id, user, auth_repo)
        except Exception as exc:
            assert exc.status_code == 403
        else:  # pragma: no cover
            raise AssertionError("source-level access unexpectedly granted")


def _client_with_user(
    engine: Engine, tmp_path: Path, *, acl_allowed: bool
) -> tuple[TestClient, str, UUID]:
    acl = [{"type": "allow", "sid": SID_ALLOW if acl_allowed else SID_DENY, "access_mask": 1}]
    _, doc_id, _ = _setup_acl_doc(engine, acl_data=acl)
    file_path = tmp_path / "doc.txt"
    file_path.write_text("hello acl", encoding="utf-8")
    with engine.begin() as connection:
        connection.execute(
            sa.text("UPDATE documents SET path = :path WHERE id = :id"),
            {"path": str(file_path), "id": db_uuid(doc_id)},
        )
    app = create_app(
        engine,
        Settings(auth_provider="local", jwt_secret=TEST_JWT_SECRET, files_root=tmp_path),
    )
    client = TestClient(app)
    token = client.post("/auth/login", json={"email": "user@example.com", "password": "secret"})
    assert token.status_code == 200
    return client, str(token.json()["access_token"]), doc_id


def test_preview_and_download_blocked_by_acl(migrated_engine: Engine, tmp_path: Path) -> None:
    client, token, doc_id = _client_with_user(migrated_engine, tmp_path, acl_allowed=False)
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get(f"/preview/{doc_id}", headers=headers).status_code == 403
    assert client.get(f"/download/{doc_id}", headers=headers).status_code == 403


def test_search_post_filter_removes_acl_denied_docs(
    migrated_engine: Engine, tmp_path: Path
) -> None:
    client, token, doc_id = _client_with_user(migrated_engine, tmp_path, acl_allowed=False)
    client.app.state.es_client = MagicMock()
    client.app.state.es_client.search.return_value = [SearchResult(doc_id=str(doc_id), score=1.0)]
    client.app.state.qdrant_client = MagicMock()
    client.app.state.qdrant_client.search.return_value = []

    response = client.post(
        "/search",
        json={"query": "hello", "page": 1, "page_size": 10},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_qa_rag_chunks_filtered_by_acl(migrated_engine: Engine, tmp_path: Path) -> None:
    client, token, doc_id = _client_with_user(migrated_engine, tmp_path, acl_allowed=False)
    client.app.state.qdrant_client = MagicMock()
    client.app.state.qdrant_client.search.return_value = [
        SearchResult(doc_id=str(doc_id), score=1.0, chunk_text="secret chunk")
    ]
    client.app.state.ollama_client = MagicMock()
    client.app.state.ollama_client._model = "mock"

    response = client.post(
        "/qa",
        json={"question": "what", "top_k": 5},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["citations"] == []
    client.app.state.ollama_client.generate.assert_not_called()


def test_non_smb_source_behavior_unchanged(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        _enable_global(connection, True)
        auth_repo = AuthRepository(connection)
        user = auth_repo.create_local_user(
            email="folder-user@example.com",
            password_hash=hash_password("secret"),
            group_names=["folder"],
        )
        source_id = auth_repo.create_ingestion_source("Folder Source")
        auth_repo.grant_source_to_group(source_id, user.groups[0])
        doc_id = auth_repo.create_document(source_id)
        assert check_doc_acl_access(doc_id, source_id, user, connection) is True


def test_mapping_crud_and_empty_principal_validation(migrated_engine: Engine) -> None:
    source_id, _, user = _setup_acl_doc(migrated_engine, acl_data=[])
    with migrated_engine.begin() as connection:
        acl_repo = SmbAclRepository(connection)
        row = acl_repo.create_mapping(source_id, "corp\\new_team", user.groups[0])
        mappings = acl_repo.list_mappings(source_id)

        assert row["windows_principal"] == "CORP\\NEW_TEAM"
        assert any(item["id"] == row["id"] for item in mappings)
        assert acl_repo.delete_mapping(source_id, UUID(str(row["id"]))) is True
        assert acl_repo.delete_mapping(source_id, UUID(str(row["id"]))) is False
        try:
            acl_repo.create_mapping(source_id, " ", user.groups[0])
        except ValueError as exc:
            assert "windows_principal" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("empty principal mapping unexpectedly accepted")


def test_acl_helpers_fail_closed_for_no_user_groups_and_malformed_acl(
    migrated_engine: Engine,
) -> None:
    source_id, doc_id, user = _setup_acl_doc(
        migrated_engine,
        acl_data=[{"type": "allow", "sid": SID_ALLOW, "access_mask": 1}],
    )
    with migrated_engine.begin() as connection:
        acl_repo = SmbAclRepository(connection)
        assert acl_repo.source_ids_for_documents([]) == {}
        assert acl_repo.can_user_access_acl(doc_id, source_id, []) is False
        acl_repo.upsert_document_acl(
            doc_id,
            [{"type": "unsupported", "sid": SID_ALLOW, "access_mask": 1}],
        )
        assert check_doc_acl_access(doc_id, source_id, user, connection) is False
        acl_repo.upsert_document_acl(
            doc_id,
            [{"type": "allow", "sid": SID_ALLOW, "access_mask": "not-an-int"}],
        )
        assert check_doc_acl_access(doc_id, source_id, user, connection) is False
