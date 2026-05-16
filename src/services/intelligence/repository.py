"""Database access for intelligence outputs (summaries, entities, tags)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from shared.db import db_uuid


class IntelligenceRepository:
    """Upsert and query intelligence outputs for documents."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def upsert_summary(self, documantions_id: UUID, summary: str, model: str) -> None:
        """Insert or update the summary for a document."""
        self._connection.execute(
            sa.text("""
                INSERT INTO document_summaries (documantions_id, summary, model)
                VALUES (:documantions_id, :summary, :model)
                ON CONFLICT (documantions_id)
                DO UPDATE SET
                    summary = EXCLUDED.summary,
                    model = EXCLUDED.model,
                    updated_at = CURRENT_TIMESTAMP
                """),
            {
                "documantions_id": db_uuid(documantions_id),
                "summary": summary,
                "model": model,
            },
        )

    def get_summary(self, documantions_id: UUID) -> dict[str, Any] | None:
        """Return the summary for a document, or None."""
        row = (
            self._connection.execute(
                sa.text("""
                    SELECT documantions_id, summary, model, created_at, updated_at
                    FROM document_summaries
                    WHERE documantions_id = :documantions_id
                    """),
                {"documantions_id": db_uuid(documantions_id)},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def upsert_entity(self, name: str, entity_type: str) -> UUID:
        """Upsert an entity by (name, type) and return its id.

        Uses INSERT ... ON CONFLICT to deduplicate.
        """
        entity_id = uuid4()
        self._connection.execute(
            sa.text("""
                INSERT INTO entities (id, name, type)
                VALUES (:id, :name, :type)
                ON CONFLICT (name, type)
                DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """),
            {
                "id": db_uuid(entity_id),
                "name": name,
                "type": entity_type,
            },
        )
        # Re-fetch to get the actual id (whether inserted or existing)
        row = (
            self._connection.execute(
                sa.text("""
                    SELECT id FROM entities
                    WHERE name = :name AND type = :type
                    """),
                {"name": name, "type": entity_type},
            )
            .mappings()
            .first()
        )
        if row is None:
            raise RuntimeError("entity upsert did not persist")
        return UUID(str(row["id"]))

    def link_document_entity(
        self,
        documantions_id: UUID,
        entity_id: UUID,
        frequency: int = 1,
    ) -> None:
        """Link a document to an entity, incrementing frequency on conflict."""
        self._connection.execute(
            sa.text("""
                INSERT INTO document_entities (documantions_id, entity_id, frequency)
                VALUES (:documantions_id, :entity_id, :frequency)
                ON CONFLICT (documantions_id, entity_id)
                DO UPDATE SET
                    frequency = document_entities.frequency + EXCLUDED.frequency
                """),
            {
                "documantions_id": db_uuid(documantions_id),
                "entity_id": db_uuid(entity_id),
                "frequency": frequency,
            },
        )

    def get_entities(self, documantions_id: UUID) -> list[dict[str, Any]]:
        """Return all entities linked to a document."""
        rows = self._connection.execute(
            sa.text("""
                SELECT e.id, e.name, e.type, de.frequency
                FROM document_entities de
                JOIN entities e ON e.id = de.entity_id
                WHERE de.documantions_id = :documantions_id
                ORDER BY de.frequency DESC, e.name
                """),
            {"documantions_id": db_uuid(documantions_id)},
        ).mappings()
        return [dict(row) for row in rows]

    def replace_tags(self, documantions_id: UUID, tags: list[str]) -> None:
        """Replace all tags for a document with the given list."""
        self._connection.execute(
            sa.text(
                "DELETE FROM document_tags WHERE documantions_id = :documantions_id"
            ),
            {"documantions_id": db_uuid(documantions_id)},
        )
        if not tags:
            return
        self._connection.execute(
            sa.text("""
                INSERT INTO document_tags (documantions_id, tag)
                VALUES (:documantions_id, :tag)
                """),
            [{"documantions_id": db_uuid(documantions_id), "tag": tag} for tag in tags],
        )

    def get_tags(self, documantions_id: UUID) -> list[str]:
        """Return all tags for a document."""
        rows = self._connection.execute(
            sa.text("""
                SELECT tag FROM document_tags
                WHERE documantions_id = :documantions_id
                ORDER BY tag
                """),
            {"documantions_id": db_uuid(documantions_id)},
        ).scalars()
        return list(rows)
