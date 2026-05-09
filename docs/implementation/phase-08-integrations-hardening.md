# Phase 08: Productization, UI, And Production Compose

## Goal

Turn the completed backend capability set into a usable local-first product.
Docker Compose should start infrastructure, backend services, and the browser UI
together, and a user should be able to complete the main workflows without
mocked services.

## Scope

- Production-oriented Docker runtime for API, frontend, migrations, and required
  infrastructure.
- Browser UI for the main user product.
- Real API wiring for auth, search, preview/download, Q&A, comments,
  annotations, subscriptions/notifications, related documents, and expertise.
- No-mock Compose smoke test covering the main product path.
- Production documentation for local deployment, reset, backup, and operations.

## Out Of Scope

- NiFi integration.
- Confluence Server/Data Center polling.
- Jira Server/Data Center polling.
- Old Microsoft Office binary extraction (`.doc`, `.xls`, `.ppt`).
- Kafka consumer wiring that is not required for the production UI milestone.

These optional integration items move to Phase 09.

## Phase 08a: Compose Runtime Foundation

Branch: `developer/phase-08a-compose-runtime`

### Scope

- Add production-oriented backend and frontend Dockerfiles.
- Add Compose services for API, frontend, migrations, Postgres, Elasticsearch,
  Qdrant, LibreTranslate, Ollama, and Redpanda if still required.
- Add `.env.example`, service healthchecks, persistent volumes, startup
  ordering, and documented local production commands.
- Add a public API health endpoint for container healthchecks.
- Document runtime operation in `docs/operations/production-compose.md`.
- Do not invent fake long-running worker containers. Only add worker containers
  when a real entrypoint exists.

### Validation

- `docker compose config`
- Clean-volume migration smoke.
- API healthcheck through Compose.
- Frontend container healthcheck through Compose.
- Existing backend validation remains green.

## Phase 08b: Frontend Foundation

Branch: `developer/phase-08b-frontend-foundation`

### Scope

- Scaffold React + TypeScript + Vite frontend using
  `docs/implementation/frontend-ui-plan.md`.
- Implement auth shell, API client, route setup, design tokens, app shell, and
  reusable primitives.
- Wire the frontend container to the API through Compose.

### Validation

- `npm --prefix frontend run lint`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`
- Responsive screenshot smoke for shell-level routes.

## Phase 08c: Main User Product UI

Branch: `developer/phase-08c-main-product-ui`

### Scope

- Implement search workspace.
- Implement document preview and download.
- Implement Q&A, comments, annotations, subscriptions/notifications, related
  documents, and expertise views against real backend APIs.
- Keep admin UI out of scope unless needed for smoke setup.
- Wire keyboard shortcut `/` to focus the search input from any authenticated
  route (append to the global key handler in AppShell or a top-level
  `useEffect`; must not trigger inside `<input>`, `<textarea>`, or
  `[contenteditable]` elements).

### Validation

- Component tests for each feature surface.
- Playwright workflows for login, search, preview/download, Q&A, annotations,
  comments, subscriptions, related documents, and expertise.
- Permission-safe states do not reveal inaccessible document metadata.
- Responsive screenshot checks at the standard UI plan viewports.

## Phase 08d: Production Smoke And Hardening

Branch: `developer/phase-08d-production-smoke`

### Scope

- Add a no-mock Compose smoke test:
  authenticate, ingest a fixture document, search it, preview it, download it,
  and load the UI.
- Add local production docs for startup, shutdown, reset, backup, environment
  variables, and common troubleshooting.
- Review security and operational defaults for local production use.

### Validation

- Full backend CI.
- Full frontend CI.
- `docker compose config`
- No-mock Compose smoke test using real local services.
- Dependency audit and secret scan.

## Acceptance Criteria

- `docker compose up` starts a working local product with backend, UI, and
  required infrastructure.
- A browser user can complete the main product workflows without mocks.
- Clean Compose volumes can be migrated from scratch.
- Production docs are sufficient for a local operator to start, stop, reset,
  back up, and troubleshoot the system.
