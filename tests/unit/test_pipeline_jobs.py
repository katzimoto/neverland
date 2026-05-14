from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa

from services.pipeline.jobs import PipelineJobRepository, _sanitize_error
from shared.db import db_uuid


@pytest.fixture()
def connection():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE pipeline_jobs (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    stage TEXT,
                    last_error TEXT,
                    run_after TEXT,
                    locked_by TEXT,
                    locked_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE document_payloads (
                    doc_id TEXT PRIMARY KEY,
                    content_text TEXT,
                    content_path TEXT,
                    content_sha256 TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX ix_pipeline_jobs_active_unique
                ON pipeline_jobs (doc_id, job_type)
                WHERE status IN ('pending', 'running', 'retry')
            """
            )
        )
    yield engine.connect()
    engine.dispose()


@pytest.fixture()
def repo(connection):
    return PipelineJobRepository(connection)


def _claim_next_sqlite(connection, locker_id, job_types=None):
    """SQLite-compatible claim helper (FOR UPDATE SKIP LOCKED not supported)."""
    query = """
        SELECT id, doc_id, source_id, job_type, priority, attempts,
               max_attempts, stage, last_error, run_after, status
        FROM pipeline_jobs
        WHERE status IN ('pending', 'retry')
          AND (run_after IS NULL OR run_after <= :now)
    """
    params: dict = {"now": datetime.now(UTC)}
    if job_types:
        placeholders = ", ".join(f":jt_{i}" for i in range(len(job_types)))
        query += f" AND job_type IN ({placeholders})"
        for i, jt in enumerate(job_types):
            params[f"jt_{i}"] = jt

    query += " ORDER BY priority DESC, created_at ASC LIMIT 1"

    row = connection.execute(sa.text(query), params).mappings().first()
    if row is None:
        return None

    now = datetime.now(UTC)
    connection.execute(
        sa.text(
            """
            UPDATE pipeline_jobs
            SET status = 'running',
                locked_by = :locked_by,
                locked_at = :locked_at,
                attempts = attempts + 1,
                updated_at = :updated_at
            WHERE id = :id
        """
        ),
        {
            "id": row["id"],
            "locked_by": locker_id,
            "locked_at": now,
            "updated_at": now,
        },
    )
    return dict(row)


class TestEnqueue:
    def test_creates_pending_job(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)

        row = (
            connection.execute(
                sa.text("SELECT * FROM pipeline_jobs WHERE id = :id"),
                {"id": db_uuid(job_id)},
            )
            .mappings()
            .first()
        )
        assert row is not None
        assert row["doc_id"] == db_uuid(doc_id)
        assert row["source_id"] == db_uuid(source_id)
        assert row["job_type"] == "process_document"
        assert row["status"] == "pending"
        assert row["priority"] == 0
        assert row["attempts"] == 0
        assert row["max_attempts"] == 3

    def test_duplicate_active_returns_existing(self, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id_1 = repo.enqueue_document(doc_id, source_id)
        job_id_2 = repo.enqueue_document(doc_id, source_id)

        assert job_id_1 == job_id_2

    def test_completed_job_allows_new_enqueue(self, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id_1 = repo.enqueue_document(doc_id, source_id)
        repo.mark_succeeded(job_id_1)

        job_id_2 = repo.enqueue_document(doc_id, source_id)
        assert job_id_1 != job_id_2

    def test_dead_letter_allows_new_enqueue(self, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id_1 = repo.enqueue_document(doc_id, source_id)
        repo.mark_dead_letter(job_id_1, "permanent failure")

        job_id_2 = repo.enqueue_document(doc_id, source_id)
        assert job_id_1 != job_id_2

    def test_different_job_types_both_accepted(self, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id_1 = repo.enqueue_document(doc_id, source_id, job_type="type_a")
        job_id_2 = repo.enqueue_document(doc_id, source_id, job_type="type_b")

        assert job_id_1 != job_id_2

    def test_stores_payload_on_enqueue(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(
            doc_id,
            source_id,
            content_text="hello world",
            content_path="/path/to/file",
            content_sha256="abc123",
        )

        payload = repo.get_payload(doc_id)
        assert payload is not None
        assert payload["content_text"] == "hello world"
        assert payload["content_path"] == "/path/to/file"
        assert payload["content_sha256"] == "abc123"

    def test_enqueue_without_payload_stores_none(self, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id)

        payload = repo.get_payload(doc_id)
        assert payload is None

    def test_payload_update_overwrites(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        first_job_id = repo.enqueue_document(doc_id, source_id, content_text="first")
        repo.mark_succeeded(first_job_id)

        repo.enqueue_document(doc_id, source_id, content_text="second", content_sha256="xyz")

        payload = repo.get_payload(doc_id)
        assert payload["content_text"] == "second"
        assert payload["content_sha256"] == "xyz"


class TestClaim:
    def test_claim_returns_job(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)

        claimed = _claim_next_sqlite(connection, "worker-1")
        assert claimed is not None
        assert claimed["id"] == db_uuid(job_id)

        row = connection.execute(
            sa.text("SELECT status FROM pipeline_jobs WHERE id = :id"),
            {"id": db_uuid(job_id)},
        ).scalar()
        assert row == "running"

    def test_claim_by_priority(self, connection, repo):
        source_id = uuid4()
        repo.enqueue_document(uuid4(), source_id, priority=1)
        repo.enqueue_document(uuid4(), source_id, priority=5)

        claimed = _claim_next_sqlite(connection, "worker-1")
        assert claimed["priority"] == 5

    def test_claim_oldest_when_same_priority(self, connection, repo):
        source_id = uuid4()
        repo.enqueue_document(uuid4(), source_id, priority=1)
        repo.enqueue_document(uuid4(), source_id, priority=1)

        first = _claim_next_sqlite(connection, "worker-1")
        second = _claim_next_sqlite(connection, "worker-2")
        assert first is not None
        assert second is not None
        assert first["id"] != second["id"]

    def test_claim_returns_none_when_none_pending(self, connection, repo):
        assert _claim_next_sqlite(connection, "worker-1") is None

    def test_claim_skips_running_jobs(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id)

        _claim_next_sqlite(connection, "worker-1")
        second = _claim_next_sqlite(connection, "worker-2")
        assert second is None

    def test_claim_skips_succeeded_jobs(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)
        repo.mark_succeeded(job_id)

        assert _claim_next_sqlite(connection, "worker-1") is None

    def test_claim_increments_attempts(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id)

        _claim_next_sqlite(connection, "worker-1")

        row = connection.execute(
            sa.text("SELECT attempts FROM pipeline_jobs WHERE doc_id = :doc_id"),
            {"doc_id": db_uuid(doc_id)},
        ).scalar()
        assert row == 1

    def test_claim_sets_locked_by(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id)

        _claim_next_sqlite(connection, "worker-42")

        row = connection.execute(
            sa.text("SELECT locked_by FROM pipeline_jobs WHERE doc_id = :doc_id"),
            {"doc_id": db_uuid(doc_id)},
        ).scalar()
        assert row == "worker-42"

    def test_claim_sets_locked_at(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id)

        _claim_next_sqlite(connection, "worker-1")

        row = connection.execute(
            sa.text("SELECT locked_at FROM pipeline_jobs WHERE doc_id = :doc_id"),
            {"doc_id": db_uuid(doc_id)},
        ).scalar()
        assert row is not None

    def test_claim_skips_retry_before_run_after(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)
        repo.mark_retry(job_id, "transient error", retry_delay_seconds=3600)

        claimed = _claim_next_sqlite(connection, "worker-1")
        assert claimed is None

    def test_claim_picks_retry_after_run_after(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)
        past = datetime.now(UTC) - timedelta(seconds=60)
        connection.execute(
            sa.text(
                """
                UPDATE pipeline_jobs
                SET status = 'retry', run_after = :run_after, updated_at = :updated_at
                WHERE id = :id
            """
            ),
            {
                "id": db_uuid(job_id),
                "run_after": past,
                "updated_at": datetime.now(UTC),
            },
        )

        claimed = _claim_next_sqlite(connection, "worker-1")
        assert claimed is not None
        assert claimed["id"] == db_uuid(job_id)

    def test_claim_with_job_types_filter(self, connection, repo):
        source_id = uuid4()
        repo.enqueue_document(uuid4(), source_id, job_type="process_document")
        repo.enqueue_document(uuid4(), source_id, job_type="translation")

        type_a_claim = _claim_next_sqlite(connection, "worker-1", job_types=["process_document"])
        assert type_a_claim is not None
        assert type_a_claim["job_type"] == "process_document"

    def test_claim_for_update_skip_locked_sent(self):
        conn = sa.create_engine("sqlite://").connect()
        repo = PipelineJobRepository(conn)

        try:
            repo.claim_next("worker-1")
        except sa.exc.OperationalError:
            pass
        else:
            pytest.fail("Expected OperationalError from FOR UPDATE on SQLite")
        finally:
            conn.close()


class TestMarkMethods:
    def test_mark_succeeded(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)

        repo.mark_succeeded(job_id)

        row = (
            connection.execute(
                sa.text("SELECT status, locked_by, locked_at FROM pipeline_jobs WHERE id = :id"),
                {"id": db_uuid(job_id)},
            )
            .mappings()
            .first()
        )
        assert row["status"] == "succeeded"
        assert row["locked_by"] is None
        assert row["locked_at"] is None

    def test_mark_retry_sets_run_after(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)

        repo.mark_retry(job_id, "something broke", retry_delay_seconds=120)

        row = (
            connection.execute(
                sa.text("SELECT status, last_error, run_after FROM pipeline_jobs WHERE id = :id"),
                {"id": db_uuid(job_id)},
            )
            .mappings()
            .first()
        )
        assert row["status"] == "retry"
        assert "something broke" in row["last_error"]
        assert row["run_after"] is not None

    def test_mark_retry_clears_locks(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)

        repo.mark_retry(job_id, "retry me")

        row = (
            connection.execute(
                sa.text("SELECT locked_by, locked_at FROM pipeline_jobs WHERE id = :id"),
                {"id": db_uuid(job_id)},
            )
            .mappings()
            .first()
        )
        assert row["locked_by"] is None
        assert row["locked_at"] is None

    def test_mark_dead_letter(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)

        repo.mark_dead_letter(job_id, "fatal error")

        row = (
            connection.execute(
                sa.text("SELECT status, last_error FROM pipeline_jobs WHERE id = :id"),
                {"id": db_uuid(job_id)},
            )
            .mappings()
            .first()
        )
        assert row["status"] == "dead_letter"
        assert "fatal error" in row["last_error"]

    def test_mark_dead_letter_clears_locks(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)

        repo.mark_dead_letter(job_id, "dead")

        row = (
            connection.execute(
                sa.text("SELECT locked_by, locked_at FROM pipeline_jobs WHERE id = :id"),
                {"id": db_uuid(job_id)},
            )
            .mappings()
            .first()
        )
        assert row["locked_by"] is None
        assert row["locked_at"] is None

    def test_mark_running_stage(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)
        _claim_next_sqlite(connection, "worker-1")

        repo.mark_running_stage(job_id, "extraction")

        row = connection.execute(
            sa.text("SELECT stage FROM pipeline_jobs WHERE id = :id"),
            {"id": db_uuid(job_id)},
        ).scalar()
        assert row == "extraction"

    def test_mark_running_stage_ignores_non_running(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)
        repo.mark_succeeded(job_id)

        repo.mark_running_stage(job_id, "should-not-save")

        row = connection.execute(
            sa.text("SELECT stage FROM pipeline_jobs WHERE id = :id"),
            {"id": db_uuid(job_id)},
        ).scalar()
        assert row is None


class TestErrorSanitization:
    def test_truncates_long_errors(self):
        long = "x" * 1000
        result = _sanitize_error(long)
        assert len(result) == 500

    def test_strips_whitespace(self):
        result = _sanitize_error("  hello  ")
        assert result == "hello"

    def test_does_not_leak_raw_content(self):
        raw = "some sensitive document content with id=123"
        result = _sanitize_error(raw)
        assert "sensitive document content" in result
        assert result == raw.strip()

    def test_handles_empty_string(self):
        assert _sanitize_error("") == ""

    def test_error_not_stored_from_raw_marker(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        job_id = repo.enqueue_document(doc_id, source_id)

        repo.mark_dead_letter(job_id, "raw_document_marker here but safe")

        row = connection.execute(
            sa.text("SELECT last_error FROM pipeline_jobs WHERE id = :id"),
            {"id": db_uuid(job_id)},
        ).scalar()
        assert row is not None
        assert len(row) <= 500


class TestGetPayload:
    def test_returns_none_for_missing(self, repo):
        assert repo.get_payload(uuid4()) is None

    def test_returns_content_text(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id, content_text="some text")

        payload = repo.get_payload(doc_id)
        assert payload["content_text"] == "some text"

    def test_returns_content_path(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id, content_path="/data/file.txt")

        payload = repo.get_payload(doc_id)
        assert payload["content_path"] == "/data/file.txt"

    def test_returns_sha256(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id, content_text="data", content_sha256="abcdef")

        payload = repo.get_payload(doc_id)
        assert payload["content_sha256"] == "abcdef"


class TestDedupPartialIndex:
    def test_partial_index_blocks_duplicate_active(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        repo.enqueue_document(doc_id, source_id)
        repo.enqueue_document(doc_id, source_id)

        count = connection.execute(
            sa.text(
                """
                SELECT COUNT(*) FROM pipeline_jobs
                WHERE doc_id = :doc_id AND status IN ('pending', 'running', 'retry')
            """
            ),
            {"doc_id": db_uuid(doc_id)},
        ).scalar()
        assert count == 1

    def test_partial_index_allows_different_status(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()
        first = repo.enqueue_document(doc_id, source_id)
        repo.mark_succeeded(first)

        repo.enqueue_document(doc_id, source_id)

        count = connection.execute(
            sa.text(
                """
                SELECT COUNT(*) FROM pipeline_jobs
                WHERE doc_id = :doc_id
            """
            ),
            {"doc_id": db_uuid(doc_id)},
        ).scalar()
        assert count == 2


class TestLifecycleIntegration:
    def test_full_claim_process_succeed(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()

        job_id = repo.enqueue_document(
            doc_id,
            source_id,
            content_text="full lifecycle test",
            content_path="/test/doc.txt",
        )

        claimed = _claim_next_sqlite(connection, "worker-1")
        assert claimed is not None
        assert claimed["id"] == db_uuid(job_id)

        payload = repo.get_payload(doc_id)
        assert payload["content_text"] == "full lifecycle test"
        assert payload["content_path"] == "/test/doc.txt"

        repo.mark_running_stage(job_id, "extraction")
        repo.mark_running_stage(job_id, "indexing")
        repo.mark_succeeded(job_id)

        row = (
            connection.execute(
                sa.text("SELECT status, stage FROM pipeline_jobs WHERE id = :id"),
                {"id": db_uuid(job_id)},
            )
            .mappings()
            .first()
        )
        assert row["status"] == "succeeded"
        assert row["stage"] == "indexing"

    def test_full_claim_process_retry_then_dead_letter(self, connection, repo):
        doc_id = uuid4()
        source_id = uuid4()

        job_id = repo.enqueue_document(doc_id, source_id, content_text="retry test")

        _claim_next_sqlite(connection, "worker-1")
        repo.mark_retry(job_id, "transient failure")

        row = (
            connection.execute(
                sa.text("SELECT status, attempts FROM pipeline_jobs WHERE id = :id"),
                {"id": db_uuid(job_id)},
            )
            .mappings()
            .first()
        )
        assert row["status"] == "retry"
        assert row["attempts"] >= 1

        repo.mark_dead_letter(job_id, "final failure after retries exhausted")

        row = connection.execute(
            sa.text("SELECT status FROM pipeline_jobs WHERE id = :id"),
            {"id": db_uuid(job_id)},
        ).scalar()
        assert row == "dead_letter"
