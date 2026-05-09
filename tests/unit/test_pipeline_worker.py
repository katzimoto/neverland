"""Unit tests for pipeline worker orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from services.documents.models import DocumentRow
from services.pipeline.worker import PipelineWorker


def test_pipeline_batches_chunk_encoding() -> None:
    doc_id = uuid4()
    source_id = uuid4()
    doc = DocumentRow(
        id=doc_id,
        source_id=source_id,
        external_id="x",
        source="folder",
        mime_type="text/plain",
        title="Doc",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repo = MagicMock()
    repo.get_by_id.return_value = doc
    repo.source_group_ids.return_value = [uuid4()]
    translator = MagicMock()
    translator.translate.return_value = "one two. " * 600
    encoder = MagicMock()
    encoder.encode_batch.return_value = [[float(i)] for i in range(10)]
    es_client = MagicMock()
    qdrant_client = MagicMock()

    worker = PipelineWorker(
        document_repository=repo,
        extractor_registry=MagicMock(),
        translator=translator,
        encoder=encoder,
        es_client=es_client,
        qdrant_client=qdrant_client,
    )

    worker.process_document(doc_id, pre_extracted_text="bonjour")

    encoder.encode_batch.assert_called_once()
    chunks = encoder.encode_batch.call_args.args[0]
    assert len(chunks) > 1
    assert not encoder.encode.called
    uploaded_chunks = qdrant_client.upsert_chunks.call_args.args[0]
    assert [chunk["vector"] for chunk in uploaded_chunks] == encoder.encode_batch.return_value[
        : len(uploaded_chunks)
    ]
