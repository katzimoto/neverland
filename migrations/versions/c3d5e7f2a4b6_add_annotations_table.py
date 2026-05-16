"""add annotations table

Revision ID: c3d5e7f2a4b6
Revises: b2c4d6e8f1a3
Create Date: 2026-05-08 15:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d5e7f2a4b6"
down_revision: str | None = "b2c4d6e8f1a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "annotations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "documantions_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("position", sa.JSON(), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_annotations_doc_id", "annotations", ["documantions_id"])
    op.create_index("ix_annotations_user_id", "annotations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_annotations_user_id", table_name="annotations")
    op.drop_index("ix_annotations_doc_id", table_name="annotations")
    op.drop_table("annotations")
