"""add smb acl tables

Revision ID: 9a1b2c3d4e5f
Revises: e5f7a9b1c3d4
Create Date: 2026-05-10 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9a1b2c3d4e5f"
down_revision: str | None = "e5f7a9b1c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_acls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("acl_data", sa.JSON(), nullable=False),
        sa.Column("acl_hash", sa.Text(), nullable=True),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_document_acls_document_id", "document_acls", ["document_id"])

    op.create_table(
        "smb_principal_mappings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Uuid(),
            sa.ForeignKey("ingestion_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("windows_principal", sa.Text(), nullable=False),
        sa.Column(
            "group_id",
            sa.Uuid(),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_id",
            "windows_principal",
            name="uq_smb_principal_source_principal",
        ),
    )
    op.create_index(
        "ix_smb_principal_mappings_source_id",
        "smb_principal_mappings",
        ["source_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_smb_principal_mappings_source_id", table_name="smb_principal_mappings")
    op.drop_table("smb_principal_mappings")
    op.drop_index("ix_document_acls_document_id", table_name="document_acls")
    op.drop_table("document_acls")
