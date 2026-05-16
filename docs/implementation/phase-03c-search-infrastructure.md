# Phase 03c: Search Infrastructure

## Goal

Create and manage the Elasticsearch index and Qdrant collection, with a mock
embedding encoder.

## Scope

- Elasticsearch client and document index mapping.
- Qdrant client and chunk collection creation.
- Mock embedding encoder (384-dim, deterministic, zero dependencies).
- Hybrid score merger for BM25 + vector results.

## Implementation Notes

- **MockEncoder** produces deterministic 384-dimensional vectors derived from
  the hash of the input text. This keeps CI fast and removes the torch
  dependency until Phase 06.
- **Elasticsearch** indexes the full document (`content_english`, `title`,
  `summary`, `tags`, `metadata`, `allowed_group_ids`).
- **Qdrant** stores one point per chunk. Payload fields: `document_id`, `group_id`,
  `chunk_index`, `text`.
- **Hybrid merge** retrieves the top 50 results from each backend, deduplicates
  by `document_id`, and scores with `vector_weight * vector_score +
  bm25_weight * bm25_score`. Weights are read from `system_config`.

## Validation

- Unit tests for mock encoder shape and determinism.
- Unit tests for Elasticsearch index/search with a mocked client.
- Unit tests for Qdrant index/search with a mocked client.
- Unit tests for hybrid merge logic (score math, deduplication, tie-breaking).

## Acceptance Criteria

- A document and its chunks can be indexed manually and retrieved by hybrid
  search.
- Search results respect the configured BM25 / vector weight ratio.
- No external model is downloaded during tests or CI.
