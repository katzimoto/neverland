# Phase 08f: Production Smoke And Hardening

## Prerequisite

None. This phase is fully independent of all frontend work and can start at
any point after Phase 08b is merged. It can run in parallel with 08c, 08d, and
08e.

## Branch

`developer/phase-08f-production-smoke`

## Scope

### No-Mock Compose Smoke Test

Add `scripts/smoke-test.sh` — a self-contained script that validates the full
product path against a running Compose stack with no mocked services:

1. Start all services: `docker compose up --build -d`.
2. Wait for API readiness: poll `GET http://localhost:8000/health` until `200`
   or timeout after 120 seconds.
3. Authenticate: `POST /auth/login` with fixture credentials from `.env.example`
   or a test env file. Capture the bearer token.
4. Create an ingestion source pointing to a fixture document directory, or
   place a small plain-text fixture file in the watched folder if the pipeline
   processes it automatically.
5. Trigger ingestion (use the existing admin API endpoint) and wait for the
   document to appear in search results (poll with retry, max 60 seconds).
6. Search: `POST /search` with the fixture document title; assert at least one
   result in the response.
7. Preview: `GET /preview/{doc_id}` using the fixture document ID; assert a
   non-empty response body.
8. Download: `GET /download/{doc_id}`; assert HTTP `200` and a non-empty
   `Content-Type` header.
9. Frontend: `GET http://localhost:8080`; assert HTTP `200` HTML response
   containing the app root element.
10. Teardown: `docker compose down -v`.

The smoke test must run entirely from `docker compose` and the script without
manual steps. It should exit non-zero on any assertion failure.

### Production Operations Documentation

Expand `docs/operations/production-compose.md` to cover all of the following
sections if they are not already complete:

- **Startup**: `docker compose up --build` for first run; `docker compose up`
  for subsequent runs.
- **Shutdown**: `docker compose down` (preserves volumes).
- **Data reset**: `docker compose down -v` (destroys all named volumes).
- **Backup**: list of named volumes to snapshot together
  (`postgres_data`, `files_data`, `elasticsearch_data`, `qdrant_data`,
  `ollama_data`). Include a brief `pg_dump` example:
  ```bash
  docker compose exec postgres pg_dump -U neverland neverland > backup.sql
  ```
- **Environment variables**: annotate all variables in `.env.example` with a
  one-line description of each. Mark required variables explicitly.
- **Common troubleshooting**:
  - Migration failures (check `migrate` service logs; re-run with
    `docker compose run --rm migrate`).
  - Elasticsearch index not created (check `api` service startup logs;
    indices are created on first API start).
  - Qdrant startup race (API retries on connection failure; add a `depends_on`
    healthcheck if the race persists).
  - Ollama model not downloaded (run `docker compose exec ollama ollama pull
    <model>` manually on first start).
- **Worker containers**: note that no long-running worker containers exist yet;
  pipeline processing runs synchronously through API calls.

### Security And Operational Defaults Review

Audit the following and fix any issues found:

- `JWT_SECRET` in `.env.example` must be a placeholder (e.g.
  `change-me-in-production`), never a real secret.
- CORS origins in the API configuration must not be `*` in the Compose
  production environment. Confirm that `CORS_ORIGINS` defaults to
  `http://localhost:8080` or is configurable, and that `*` is not the
  production default.
- `RELOAD` and `DEBUG` flags in the Compose `api` service environment must be
  `false` or absent.
- The safe download pattern (`safe_download` or equivalent path-validation
  guard in `src/services/api/main.py`) must be present and not bypassable.
- Confirm no hardcoded passwords, tokens, or API keys in tracked source files
  other than `.env.example` placeholder values.
- Run Python dependency audit:
  ```bash
  uv run pip-audit
  ```
- Run frontend dependency audit:
  ```bash
  npm --prefix frontend audit
  ```
- Run secret scan:
  ```bash
  git grep -rn --include="*.py" --include="*.ts" --include="*.tsx" \
    -E "(password|secret|token|api_key)\s*=\s*['\"][^$<{]" \
    | grep -v ".example" | grep -v "_test" | grep -v "# "
  ```
  Report any real secrets found; do not commit them.

## Do Not Start Criteria

This phase has no frontend route dependency, but observe these general rules:

- Do not begin if the Compose stack has known broken healthchecks that would
  cause the smoke test to hang indefinitely (fix or skip with a documented
  reason).
- Do not commit real secrets to fix audit findings; remove or rotate them
  instead.

## New Files

```
scripts/smoke-test.sh
```

## Modified Files

```
docs/operations/production-compose.md   — expand with all sections listed above
.env.example                            — annotate all variables
```

## Validation

```bash
# Backend CI
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev mypy src --strict
uv run --extra dev pytest

# Frontend CI
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run build

# Compose config
docker compose config

# Smoke test
docker compose up --build -d
bash scripts/smoke-test.sh
docker compose down -v

# Audits
uv run pip-audit
npm --prefix frontend audit
```

## Acceptance Criteria

- `docker compose up` starts the API, frontend, migration job, and all required
  infrastructure services without manual steps.
- The no-mock smoke test completes all steps: authenticate, ingest, search,
  preview, download, load UI.
- Clean-volume migration from scratch (`docker compose down -v && docker compose
  up`) succeeds.
- Production operations docs are sufficient for a local operator to start,
  stop, reset, back up, and troubleshoot the system.
- No real secrets appear in tracked files.
- `pip-audit` and `npm audit` report no critical or high vulnerabilities
  (document any accepted exceptions with justification).

Stop for Reviewer-agent review.
