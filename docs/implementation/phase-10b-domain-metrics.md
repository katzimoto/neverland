# Phase 10b: Domain Metrics

## Goal

Instrument all existing service paths with low-cardinality counters and histograms so
operators can observe the health of every major application domain.

Design source: `docs/design/metrics-monitoring-spec.md` §Metric Catalog (all domain tables).

## Phase Placement

Branch: `developer/phase-10b-domain-metrics`

Status: Planned (requires Phase 10a metrics foundation and safe label helpers).

## Dependencies

- Phase 10a metrics foundation, `/metrics` endpoint, and label helper utilities.
- All Phase 03–08 service implementations (auth, pipeline, search, translation,
  intelligence, RAG, comments, annotations, subscriptions, notifications, related).

## Scope

Instrument the following service paths. Use the metric names and label sets defined in
`docs/design/metrics-monitoring-spec.md`. Do not introduce new metric names not listed there
without updating the spec first.

### Authentication And Authorization

- `neverland_auth_login_attempts_total` — labels: `provider`, `outcome`.
- `neverland_authz_denials_total` — labels: `resource_type`, `action`.
- `neverland_admin_actions_total` — labels: `action`, `resource_type`.

### Ingestion And Pipeline

- `neverland_ingestion_syncs_total` — labels: `connector_type`, `outcome`.
- `neverland_ingestion_documents_total` — labels: `connector_type`, `outcome`.
- `neverland_pipeline_documents_total` — labels: `stage`, `outcome`.
- `neverland_pipeline_stage_duration_seconds` histogram — label: `stage`.
- `neverland_pipeline_document_bytes` histogram — label: `connector_type`.
- `neverland_pipeline_chunks_total` — labels: `outcome`.
- `neverland_dlq_records_total` — labels: `reason`, `source`.
- `neverland_dlq_pending` gauge — no labels; read from PostgreSQL at scrape time.

### Search And Retrieval

- `neverland_search_requests_total` — labels: `mode`, `outcome`.
- `neverland_search_duration_seconds` histogram — label: `mode`.
- `neverland_search_backend_duration_seconds` histogram — labels: `backend`, `operation`.
- `neverland_search_results_count` histogram — label: `mode`.
- `neverland_search_index_documents` gauge — label: `backend`.

### Translation, Intelligence, And RAG

- `neverland_translation_requests_total` — labels: `kind`, `outcome`.
- `neverland_translation_duration_seconds` histogram — label: `kind`.
- `neverland_translation_characters_total` counter — label: `kind`.
- `neverland_intelligence_tasks_total` — labels: `task`, `outcome`.
- `neverland_intelligence_task_duration_seconds` histogram — label: `task`.
- `neverland_ollama_requests_total` — labels: `operation`, `outcome`.
- `neverland_ollama_duration_seconds` histogram — label: `operation`.
- `neverland_rag_requests_total` — label: `outcome`.
- `neverland_rag_duration_seconds` histogram — label: `phase`.
- `neverland_rag_citations_count` histogram — no labels.

### Collaboration And Activity

- `neverland_preview_requests_total` — labels: `mime_family`, `outcome`.
- `neverland_download_requests_total` — label: `outcome`.
- `neverland_comments_total` — labels: `action`, `outcome`.
- `neverland_annotations_total` — labels: `action`, `visibility`, `outcome`.
- `neverland_subscriptions_total` — labels: `action`, `outcome`.
- `neverland_notifications_total` — labels: `event`, `outcome`.

## Implementation Notes

- Instrument at the service-class method level, not inside route handlers, so metrics are
  reusable by future worker entrypoints.
- Use the safe label helpers from Phase 10a for all label values.
- Mock all external services in unit tests; verify counter increments on success and failure
  paths without requiring live backends.

## Validation

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src --strict
pytest tests/unit/test_domain_metrics.py -q
```

Each instrumented service should have at least a success-path and failure-path counter
assertion.

## Acceptance Criteria

- All metric names in the catalog have at least one test asserting they increment on the
  happy path.
- Failure paths increment outcome-labeled failure counters rather than raising unhandled
  exceptions.
- No label value contains a user ID, document ID, query string, source name, or file content.
- Existing service unit tests remain green.
