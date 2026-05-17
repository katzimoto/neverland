"""rename documant_id -> document_id in all remaining tables

PR #389's bulk sed fixed src/ but missed migrations/.  g1h2i3j4k5l6 fixed
pipeline_jobs and document_payloads.  This migration fixes the remaining ten
tables that still carry the typo in production.

PostgreSQL renames column references in indexes and constraints automatically,
so no explicit drop/recreate is needed here.

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-05-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "h2i3j4k5l6m7"
down_revision: str = "g1h2i3j4k5l6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("ingested_files", "documant_id", new_column_name="document_id")
    op.alter_column("dlq", "documant_id", new_column_name="document_id")
    op.alter_column("document_translation_versions", "documant_id", new_column_name="document_id")
    op.alter_column("document_summaries", "documant_id", new_column_name="document_id")
    op.alter_column("document_entities", "documant_id", new_column_name="document_id")
    op.alter_column("document_tags", "documant_id", new_column_name="document_id")
    op.alter_column("document_views", "documant_id", new_column_name="document_id")
    op.alter_column("annotations", "documant_id", new_column_name="document_id")
    op.alter_column("alert_notifications", "documant_id", new_column_name="document_id")
    op.alter_column("document_comments", "documant_id", new_column_name="document_id")


def downgrade() -> None:
    op.alter_column("document_comments", "document_id", new_column_name="documant_id")
    op.alter_column("alert_notifications", "document_id", new_column_name="documant_id")
    op.alter_column("annotations", "document_id", new_column_name="documant_id")
    op.alter_column("document_views", "document_id", new_column_name="documant_id")
    op.alter_column("document_tags", "document_id", new_column_name="documant_id")
    op.alter_column("document_entities", "document_id", new_column_name="documant_id")
    op.alter_column("document_summaries", "document_id", new_column_name="documant_id")
    op.alter_column("document_translation_versions", "document_id", new_column_name="documant_id")
    op.alter_column("dlq", "document_id", new_column_name="documant_id")
    op.alter_column("ingested_files", "document_id", new_column_name="documant_id")
