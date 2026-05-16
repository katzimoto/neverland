from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentSource(StrEnum):
    """Supported document source types."""

    FOLDER = "folder"
    NIFI = "nifi"
    CONFLUENCE = "confluence"
    JIRA = "jira"


class DocumentOperation(StrEnum):
    """Operations carried by `documents.raw` events."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class IntelligenceTask(StrEnum):
    """Tasks carried by `documents.intelligence` events."""

    SUMMARIZE = "summarize"
    EXTRACT_ENTITIES = "extract_entities"
    MATCH_ALERTS = "match_alerts"
    AUTO_TAG = "auto_tag"


class TranslationQuality(StrEnum):
    """Known translation quality states for persisted and indexed documents."""

    FAST = "fast"
    HIGH = "high"


class DocumentStatus(StrEnum):
    """Foundation document lifecycle states."""

    PENDING = "pending"
    INDEXED = "indexed"
    DELETED = "deleted"
    FAILED = "failed"


class DocumentEvent(BaseModel):
    """Normalized event published to `documents.raw` by ingestion or NiFi."""

    model_config = ConfigDict(use_enum_values=True)

    documant_id: UUID
    source_id: UUID
    source: DocumentSource
    external_id: str = Field(min_length=1)
    path: str | None = None
    mime_type: str = Field(min_length=1)
    source_language: str | None = None
    operation: DocumentOperation
    timestamp: datetime
    correlation_id: UUID


class IntelligenceEvent(BaseModel):
    """Event published to `documents.intelligence` for best-effort LLM tasks."""

    model_config = ConfigDict(use_enum_values=True)

    documant_id: UUID
    content_english: str
    allowed_group_ids: list[UUID]
    correlation_id: UUID
    tasks: list[IntelligenceTask]
