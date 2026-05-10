from __future__ import annotations

from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from services.api.main import create_app
from services.auth.passwords import hash_password
from services.auth.repository import AuthRepository
from services.documents.repository import DocumentRepository
from services.permissions.acl_repository import SmbAclRepository
from shared.config import Settings
from shared.db import db_uuid

TEST_JWT_SECRET = "x" * 32
SID_ALLOWED = "S-1-5-21-9-8-7-1001"
SID_OTHER = "S-1-5-21-9-8-7-2001"


def _login(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "secret"})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def test_acl_enforcement_full_flow(migrated_engine: Engine, tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    file_path.write_text("allowed text", encoding="utf-8")
    with migrated_engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE system_config SET value = :value WHERE key = 'feature.smb_acl_sync'"
            ).bindparams(sa.bindparam("value", type_=sa.JSON())),
            {"value": True},
        )
        auth_repo = AuthRepository(connection)
        admin = auth_repo.create_local_user(
            email="admin@example.com",
            password_hash=hash_password("secret"),
            is_admin=True,
            group_names=["admins"],
        )
        allowed_user = auth_repo.create_local_user(
            email="allowed@example.com",
            password_hash=hash_password("secret"),
            group_names=["legal"],
        )
        denied_user = auth_repo.create_local_user(
            email="denied@example.com",
            password_hash=hash_password("secret"),
            group_names=["finance"],
        )
        source_id = auth_repo.create_ingestion_source("SMB Source", source_type="smb")
        connection.execute(
            sa.text("UPDATE ingestion_sources SET config = :config WHERE id = :id").bindparams(
                sa.bindparam("config", type_=sa.JSON())
            ),
            {"id": db_uuid(source_id), "config": {"acl_sync_enabled": True}},
        )
        auth_repo.grant_source_to_group(source_id, allowed_user.groups[0])
        auth_repo.grant_source_to_group(source_id, denied_user.groups[0])
        auth_repo.grant_source_to_group(source_id, admin.groups[0])
        doc = DocumentRepository(connection).create(
            source_id=source_id,
            external_id="smb://server/share/doc.txt",
            source="smb",
            mime_type="text/plain",
            title="Doc",
            path=str(file_path),
        )
        assert doc is not None
        acl_repo = SmbAclRepository(connection)
        acl_repo.create_mapping(source_id, SID_ALLOWED, allowed_user.groups[0])
        acl_repo.upsert_document_acl(
            doc.id,
            [{"type": "allow", "sid": SID_ALLOWED, "access_mask": 1}],
        )

    client = TestClient(
        create_app(
            migrated_engine,
            Settings(auth_provider="local", jwt_secret=TEST_JWT_SECRET, files_root=tmp_path),
        )
    )
    admin_token = _login(client, "admin@example.com")
    allowed_token = _login(client, "allowed@example.com")
    denied_token = _login(client, "denied@example.com")

    response = client.post(
        f"/admin/sources/{source_id}/acl-mappings",
        json={"windows_principal": SID_OTHER, "group_id": str(denied_user.groups[0])},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["windows_principal"] == SID_OTHER

    allowed = client.get(f"/preview/{doc.id}", headers={"Authorization": f"Bearer {allowed_token}"})
    denied = client.get(f"/preview/{doc.id}", headers={"Authorization": f"Bearer {denied_token}"})

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert UUID(response.json()["source_id"]) == source_id
