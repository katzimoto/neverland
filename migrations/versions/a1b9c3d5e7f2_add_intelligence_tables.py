"""add intelligence tables

Revision ID: a1b9c3d5e7f2
Revises: 8e3f2a9c1d56
Create Date: 2026-05-08 13:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b9c3d5e7f2"
down_revision: str | None = "8e3f2a9c1d56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_summaries",
        sa.Column(
            "doc_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
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

    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "type",
            sa.Text(),
            sa.CheckConstraint(
                "type IN ('person', 'organization', 'location', 'date')",
                name="ck_entities_type",
            ),
            nullable=False,
        ),
        sa.UniqueConstraint("name", "type", name="uq_entities_name_type"),
    )

    op.create_table(
        "document_entities",
        sa.Column(
            "doc_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            sa.Uuid(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("frequency", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("doc_id", "entity_id"),
    )
    op.create_index(
        "ix_document_entities_entity_id",
        "document_entities",
        ["entity_id"],
    )

    op.create_table(
        "document_tags",
        sa.Column(
            "doc_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tag", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("doc_id", "tag"),
    )
    op.create_index(
        "ix_document_tags_tag",
        "document_tags",
        ["tag"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_tags_tag", table_name="document_tags")
    op.drop_table("document_tags")
    op.drop_index("ix_document_entities_entity_id", table_name="document_entities")
    op.drop_table("document_entities")
    op.drop_table("entities")
    op.drop_table("document_summaries")
