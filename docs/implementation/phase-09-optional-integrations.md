# Phase 09: Optional Integrations And Legacy Format Support

## Goal

Add the remaining optional integrations and legacy document support after the
main production Compose + UI product is ready. Confluence and Jira Server/Data
Center polling are already implemented before this phase; Phase 09 should not
re-plan that shipped connector work.

## Current Atlassian Baseline

- `ConfluenceConnector` and `JiraConnector` are registered source connectors.
- The connectors validate Server/Data Center base URLs, reject Atlassian Cloud
  hosts (`atlassian.net` and subdomains), expose admin form fields, poll
  pages/issues, normalize page/issue text, and download attachments.
- Imported Atlassian documents use the same ingestion-source and source-grant
  permission model as folder-ingested documents. Page/project permission
  synchronization is not implemented.

## Scope

- NiFi event integration beyond the registered connector stub.
- Optional Atlassian hardening only if required by operators, such as
  page/project permission synchronization or stricter redirect-host policy.
- Old Microsoft Office binary extraction for `.doc`, `.xls`, and `.ppt`.
- Kafka consumer wiring that is not required for the Phase 08 production UI
  milestone.

## Decision Gates

- Decide whether Atlassian source-grant mapping remains sufficient or whether a
  future permission-sync feature is required.
- Decide whether Atlassian attachment/API redirects need explicit host allowlist
  enforcement beyond the current base URL validation.
- Confirm acceptable system dependencies for legacy Office extraction.

## Implementation Notes

- Legacy Office extractors should follow the existing extractor protocol and
  return `""` on failure without raising.
- Prefer deterministic NiFi/event and legacy extraction tests over live external
  service dependencies.
- Keep all imported documents tied to ingestion sources and source-permission
  grants.
- Do not replace the existing Confluence/Jira polling connectors unless the
  change is a narrowly scoped hardening follow-up.

## Validation

- NiFi event tests.
- Legacy Office fixture extraction tests.
- Permission filtering tests for imported documents.
- Targeted Atlassian tests only for any optional Atlassian hardening added in
  this phase.
- Existing backend CI remains green.

## Acceptance Criteria

- Optional integrations are deterministic under test.
- Integration failures route through existing operational failure paths.
- Legacy Office support does not weaken modern format extraction behavior.
- NiFi documents, and any Atlassian hardening changes, remain governed by the
  same source-grant access model as folder-ingested documents.
