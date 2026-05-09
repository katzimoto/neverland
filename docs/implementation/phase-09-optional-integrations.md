# Phase 09: Optional Integrations And Legacy Format Support

## Goal

Add enterprise integrations and legacy document support after the main
production Compose + UI product is ready.

## Scope

- NiFi event integration.
- Confluence Server/Data Center polling.
- Jira Server/Data Center polling.
- Atlassian permission and URL validation decisions.
- Old Microsoft Office binary extraction for `.doc`, `.xls`, and `.ppt`.
- Kafka consumer wiring that is not required for the Phase 08 production UI
  milestone.

## Decision Gates

- Resolve Atlassian permissions:
  define whether manual group mapping is sufficient or page/project permission
  synchronization is required.
- Resolve Atlassian URL validation:
  define exact hostname matching, `*.atlassian.net` handling, and redirect
  policy.
- Confirm acceptable system dependencies for legacy Office extraction.

## Implementation Notes

- Legacy Office extractors should follow the existing extractor protocol and
  return `""` on failure without raising.
- Prefer deterministic polling and event tests over live external service
  dependencies.
- Keep all imported documents tied to ingestion sources and source-permission
  grants.

## Validation

- Mocked Atlassian sync tests.
- NiFi event tests.
- Legacy Office fixture extraction tests.
- Permission filtering tests for imported documents.
- Existing backend CI remains green.

## Acceptance Criteria

- Optional integrations are deterministic under test.
- Integration failures route through existing operational failure paths.
- Legacy Office support does not weaken modern format extraction behavior.
- Atlassian and NiFi documents remain governed by the same source-grant access
  model as folder-ingested documents.
