"""rename documant_id to document_id in pipeline_jobs and document_payloads

The original migration created both tables with a typo in the primary/foreign-key
column name.  This migration renames the column in-place so the Python code can
use the correct spelling without touching already-applied rows.

Revision ID: g1h2i3j4k5l6
Revises: e1f2a3b4c5d6, b8c1d2e3f7a9
Create Date: 2026-05-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: tuple[str, str] = ("e1f2a3b4c5d6", "b8c1d2e3f7a9")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop indexes that reference the old column name before renaming.
    op.execute("DROP INDEX IF EXISTS ix_pipeline_jobs_active_unique")
    op.drop_index("ix_pipeline_jobs_doc_id", table_name="pipeline_jobs")

    op.alter_column("pipeline_jobs", "documant_id", new_column_name="document_id")
    op.alter_column("document_payloads", "documant_id", new_column_name="document_id")

    # Recreate indexes with the correct column name.
    op.create_index("ix_pipeline_jobs_doc_id", "pipeline_jobs", ["document_id"])
    op.execute("""
        CREATE UNIQUE INDEX ix_pipeline_jobs_active_unique
        ON pipeline_jobs (document_id, job_type)
        WHERE status IN ('pending', 'running', 'retry')
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pipeline_jobs_active_unique")
    op.drop_index("ix_pipeline_jobs_doc_id", table_name="pipeline_jobs")

    op.alter_column("pipeline_jobs", "document_id", new_column_name="documant_id")
    op.alter_column("document_payloads", "document_id", new_column_name="documant_id")

    op.create_index("ix_pipeline_jobs_doc_id", "pipeline_jobs", ["documant_id"])
    op.execute("""
        CREATE UNIQUE INDEX ix_pipeline_jobs_active_unique
        ON pipeline_jobs (documant_id, job_type)
        WHERE status IN ('pending', 'running', 'retry')
    """)
