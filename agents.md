# AGENTS.md — Neverland Developer & Reviewer Guide

> **READ THIS FIRST** if you are an AI agent joining this project.
> This file is the single source of truth for how to develop, review, and maintain Neverland.

## 1. Project Overview (30 seconds)

**Neverland** is a local-first knowledge intelligence system for private document corpora.
- **Stack:** Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Elasticsearch, Qdrant, LibreTranslate, Docker Compose
- **Architecture:** REST API + background workers (fast/slow/intelligence), air-gapped deployment
- **Current state:** Phase 07 complete through PR #20. Next up is Phase 08:
  production Compose + UI productization.

### Key docs to read first
1. `docs/logical-spec.md` — What the product does (domain, actors, capabilities)
2. `docs/implementation/README.md` — Phase index and implementation rules
3. `docs/review/spec-gaps.md` — Resolved and open architecture decisions
4. `CHANGELOG.md` — What has been built so far

### Canonical specs (read-only)
- `spec.md` and `spec-v4.pdf` — Original client requirements. Do not modify.

---

## 2. Repository Layout

```
neverland/
├── AGENTS.md              # ← You are here
├── skill.md               # Project-specific skills (TDD, lint, coverage rules)
├── CHANGELOG.md           # Release history
├── README.md              # One-liner + spec reference
├── pyproject.toml         # Python deps, pytest, ruff, mypy config
├── docker-compose.yml     # Local infrastructure (Postgres, ES, Qdrant)
│
├── src/                   # Production code
│   ├── services/
│   │   ├── api/main.py        # FastAPI app, all HTTP routes
│   │   ├── auth/              # JWT, LDAP, passwords, users/groups
│   │   ├── chunking/          # Text chunking for embedding
│   │   ├── documents/         # Document model + repository (Postgres)
│   │   ├── extraction/        # 15+ file type extractors (registry pattern)
│   │   ├── permissions/       # Group-based access enforcer
│   │   ├── pipeline/          # Fast worker + Slow worker
│   │   ├── preview/           # Preview service + view tracking
│   │   ├── search/            # ES (BM25), Qdrant (vectors), hybrid merger
│   │   └── translation/       # LibreTranslate client
│   └── shared/                # Config, DB utils, correlation IDs, events
│
├── tests/
│   ├── unit/                  # Fast, isolated tests (one per src module)
│   ├── integration/           # API + DB round-trip tests
│   └── fixtures/              # Sample files (docx, pdf, pptx, txt, xlsx)
│
├── migrations/                # Alembic migrations (numbered + timestamped)
│
├── docs/
│   ├── logical-spec.md        # Product behavior (read first)
│   ├── review/
│   │   └── spec-gaps.md       # Architecture decision log
│   ├── implementation/
│   │   ├── README.md          # Phase index
│   │   ├── phase-0N-*.md      # Per-phase implementation plans
│   │   └── frontend-ui-plan.md
│   └── design/                # UI specs, logos (non-code design assets)
│
├── review/                    # Per-PR review reports
│   └── <pr-number>.md
│
├── scripts/
│   ├── pre-commit             # Fast lint/format/type check (no tests)
│   └── install-hooks.sh       # One-time hook installer
│
└── .github/workflows/ci.yml   # CI: lint + type check + tests + security
```

---

## 3. Development Workflow

### Before you write code

1. **Check the phase plan** in `docs/implementation/phase-0N-*.md`
2. **Check blockers** in `docs/review/spec-gaps.md` — if any are open for your phase, STOP and resolve them first
3. **Check CHANGELOG.md** — understand what is already built
4. **Branch from `main`**:
   ```bash
   git checkout -b developer/phase-0N-<short-name>
   ```

### While you write code

1. **TDD cycle**: failing test → minimal pass → refactor
2. **Coverage floor:** 90% lines + branches (enforced in `pyproject.toml` and CI)
3. **Pre-commit hook runs automatically:** ruff check → ruff format → mypy (NO tests — those run in CI)
4. **Install the hook once:**
   ```bash
   ./scripts/install-hooks.sh
   ```

### Before you declare done

Run locally (same as CI but faster):
```bash
# Fast (pre-commit)
ruff check --fix src/ tests/ migrations/
ruff format src/ tests/ migrations/
mypy src --strict

# Full (CI)
pytest                    # ~2 min, 204 tests, coverage report
```

### Output contract (every PR must include)

| Artifact | Location |
|----------|----------|
| Implementation | `src/` |
| Unit tests | `tests/unit/` |
| Integration tests | `tests/integration/` |
| Migration (if schema changes) | `migrations/versions/` |
| Updated docs | `docs/implementation/` or inline docstrings |
| Changelog entry | `CHANGELOG.md` → `[Unreleased]` |
| Review file | `review/<pr-number>.md` |

---

## 4. Review Workflow

### When to review
- After Developer declares a phase complete
- Before any merge to `main`

### How to review
1. Read the PR diff: `git diff origin/main...HEAD`
2. Run the same checks as CI locally
3. Write findings to `review/<pr-number>.md` using this structure:

```markdown
## Review — PR #<number>

### ❌ Blockers (must fix before merge)
- <file>:<line> — <explanation + suggested fix>

### ⚠️ Warnings (should fix)
- <file>:<line> — <explanation>

### 💡 Suggestions (nice-to-have)
- <explanation>

### ✅ Coverage report
| Scope | Measured | Threshold | Status |
|---|---|---|---|
| Unit + Integration | ≥ 94 % | 90 % | ✅ |

### 📋 Checklist
- [x] All public symbols documented
- [x] CHANGELOG.md updated
- [x] No hardcoded secrets
- [x] Dependency audit clean
- [x] Lint: 0 errors
- [x] Migration has downgrade path
- [x] FK constraints use ON DELETE CASCADE

### Verdict
**Approved.** / **Changes requested.**
```

### Review criteria
- **Blockers:** correctness bugs, security issues, coverage below 90%, missing migrations, broken tests
- **Warnings:** style issues, missing edge-case tests, documentation gaps, performance concerns
- **Suggestions:** refactors, feature extensions, nice-to-haves

---

## 5. Code Conventions

### Python (this project)
- **Formatter:** Ruff (line length 100)
- **Linter:** Ruff with rules `E, F, W, I, N, UP, B, C4, SIM, TCH`
- **Type checker:** mypy --strict
- **Docstrings:** Google style for every public symbol
- **Imports:** `from __future__ import annotations` in every file
- **UUID handling:** Use `shared.db.db_uuid()` for SQL parameter binding

### FastAPI patterns
- All routes live in `src/services/api/main.py` (single file, ~800 lines, acceptable for MVP)
- Auth dependency: `Depends(current_user)`
- Admin guard: `require_admin(user)`
- Doc access: `assert_doc_access(doc_id, user, auth_repo)`
- DB connections: `with app.state.engine.begin() as connection:`

### Testing patterns
- Unit tests mock external services (ES, Qdrant, translator)
- Integration tests use real DB via `migrated_engine` fixture in `tests/conftest.py`
- JWT secret for tests: `"x" * 32` (see `test_enrichment.py`)
- Test helpers: `_admin_token()`, `_user_token()`, `_setup_users()`

---

## 6. Architecture Quick Reference

### Data flow
```
Ingestion Source (folder/NiFi/Atlassian)
    → POST /admin/ingest
    → PipelineWorker (fast): extract → translate → chunk → embed → index
    → Postgres (document metadata) + ES (BM25) + Qdrant (vectors)

User Search
    → POST /search (hybrid BM25 + vector)
    → Permission filter by user groups
    → Return merged results

User Preview
    → GET /preview/{doc_id}
    → Record view in document_views
    → Auto-enrich if view count ≥ threshold

Document Comments (07a)
    → GET /documents/{doc_id}/comments
    → POST /documents/{doc_id}/comments
    → PATCH /documents/{doc_id}/comments/{comment_id}
    → DELETE /documents/{doc_id}/comments/{comment_id} (soft delete)

Annotations (07b)
    → GET /documents/{doc_id}/annotations
    → POST /documents/{doc_id}/annotations
    → PUT /annotations/{annotation_id}
    → DELETE /annotations/{annotation_id} (hard delete)

RAG Q&A (07c)
    → POST /qa → {question, top_k?} → {answer, citations[], model}

Manual Translation
    → POST /documents/{doc_id}/translate
    → Set translation_quality = 'pending_high'
    → SlowWorker (background): re-extract → re-translate → re-index
```

### Translation state machine
```
null  --fast worker-->  "fast"
"fast" --manual/auto-->  "pending_high"  --slow worker-->  "high"
null  --manual/auto-->  "pending_high"  --slow worker-->  "high"
```

### Key tables
- `users`, `groups`, `user_groups` — auth
- `ingestion_sources`, `source_permissions` — document sources
- `documents` — core document metadata (status, translation_quality)
- `document_views` — per-user view tracking
- `document_comments` — per-document threaded comments (07a)
- `annotations` — per-document highlights with notes and position (07b)
- `rag_qa` — Qdrant chunks + Ollama for Q&A (07c, no new table)
- `alert_subscriptions`, `alert_notifications` — proactive document match alerts (07d)
- `system_config` — feature flags and tunables (JSON values)

---

## 7. Common Pitfalls

1. **Tests are SLOW (~2 min)** — the pre-commit hook intentionally skips them. Do not add tests back to pre-commit.
2. **SlowWorker is not wired to a trigger** — it exists and is tested, but no scheduler/API calls it yet. Wire it in Phase 06 or 08.
3. **Document status `'deleted'`** — SlowWorker does not check for this. Add a guard if enriching deleted docs becomes a risk.
4. **Auto-enrich concurrency** — `_maybe_auto_enrich` does an unconditional UPDATE. The Python guard prevents double-fire, but concurrent previews could race. Acceptable for MVP.
5. **Logo assets in Phase 05b commit** — `docs/design/assets/` and `logo-options.md` were committed with 05b but are unrelated. They are harmless but could be separated in cleanup.
6. **No `gh` CLI installed globally** — if you need `gh`, install to `~/.local/bin`:
   ```bash
   curl -fsSL https://github.com/cli/cli/releases/download/v2.69.0/gh_2.69.0_linux_amd64.tar.gz -o /tmp/gh.tar.gz
   tar -xzf /tmp/gh.tar.gz -C /tmp
   cp /tmp/gh_2.69.0_linux_amd64/bin/gh ~/.local/bin/
   ```

---

## 8. Next Phase (Phase 08)

Phase 07 is complete through PR #20. See
`docs/implementation/phase-08-integrations-hardening.md`.

Phase 08 execution order (sequential, one PR per sub-phase, stop for review after each):
1. **08a** — Compose runtime foundation (`developer/phase-08a-compose-runtime`, in development)
2. **08b** — Frontend foundation (`developer/phase-08b-frontend-foundation`)
3. **08c** — Main user product UI (`developer/phase-08c-main-product-ui`)
4. **08d** — Production smoke and hardening (`developer/phase-08d-production-smoke`)

Deferred Phase 09 scope:
- NiFi integration
- Confluence and Jira polling
- Old Office binary extraction (`.doc`, `.xls`, `.ppt`)
- Kafka consumer wiring not needed for the production UI milestone

Key decisions locked in for Phase 07:
- Alert matching trigger: Both ingest-time + admin trigger
- RAG chunk source: Qdrant payloads only (Option A)
- Expertise map: Views + annotations + comments + subscriptions
- Related documents source: Qdrant chunk vectors, permission-filtered by user groups

Key decisions locked in for Phase 08:
- Main product readiness means local production Compose plus usable browser UI
  before optional enterprise integrations.
- Compose target is single-machine/local-first production, not Kubernetes or
  cloud deployment.
- Do not add fake long-running worker containers before real worker entrypoints
  exist.

---

## 9. File Checklist for New Agents

When you start a session, read these in order:

- [ ] `AGENTS.md` (this file)
- [ ] `docs/logical-spec.md`
- [ ] `docs/implementation/README.md`
- [ ] `docs/review/spec-gaps.md`
- [ ] `CHANGELOG.md`
- [ ] `pyproject.toml` (tool config)
- [ ] `docs/implementation/phase-0N-*.md` (the phase you're working on)

Then dive into `src/` and `tests/` as needed.
