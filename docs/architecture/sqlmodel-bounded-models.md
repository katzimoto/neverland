# Architecture Decision: SQLModel for Bounded Backend Models

Issue: #111  
Status: Accepted as a guardrail; pilot deferred until explicitly scoped  
Date: 2026-05-12

## Context

Tomorrowland currently uses FastAPI with Pydantic request/response models,
SQLAlchemy Core queries, Alembic migrations, and repository methods that manually
serialize database rows into typed service/API objects. This pattern is already
used across product-critical modules such as auth, permissions, documents,
sources, comments, annotations, subscriptions, audit logs, search, and
translation-version metadata.

SQLModel could reduce duplication between persistence entities, validation
models, and API schemas for new modules. However, adopting it broadly would
change the backend data-abstraction style during release stabilization and could
create migration, transaction, typing, and agent-confusion risk.

## Decision

Do not adopt SQLModel as a broad backend migration now.

The default backend persistence pattern remains:

- explicit Alembic migrations;
- SQLAlchemy Core / bound SQL through repository classes;
- Pydantic models for request/response and service boundaries;
- explicit row-to-response serialization where routes expose API contracts.

SQLModel may be evaluated only in a bounded, explicitly authorized mission. The
best candidate remains a future new module around translation job/status records
related to Issue #110, not existing product-critical repositories.

## Allowed use of SQLModel

SQLModel is allowed only when all of these are true:

1. A GitHub issue explicitly authorizes SQLModel for a specific module.
2. The module is new or tightly bounded, with no broad rewrite of existing
   repositories.
3. Alembic migrations remain explicit, reviewable, and reversible.
4. API contracts are not changed merely to fit SQLModel entity shapes.
5. The PR includes tests for validation, persistence, repository behavior, and
   serialization.
6. The PR body explains why SQLModel improves the bounded module compared with
   the existing SQLAlchemy Core + Pydantic pattern.

## Forbidden use without explicit approval

Agents must not:

- introduce SQLModel while implementing unrelated feature work;
- migrate auth, permissions, documents, sources, comments, annotations,
  subscriptions, audit logs, or search repositories to SQLModel;
- replace existing SQLAlchemy Core repository methods broadly;
- combine a SQLModel experiment with release blockers, UI polish, security work,
  branding, or air-gapped packaging changes;
- change public API response shapes just to align with SQLModel classes;
- add SQLModel as a dependency without a mission that explicitly accepts that
  dependency change.

## Pilot candidate

If a future mission approves a pilot, the preferred scope is a new translation
worker/job-status module related to Issue #110.

A good pilot would include:

- isolated SQLModel entity definitions for the new module only;
- a repository dedicated to that module;
- explicit Alembic migration files with upgrade and downgrade paths;
- tests comparing model validation, persistence behavior, and API serialization;
- a PR section documenting tradeoffs against the existing pattern.

## Expansion criteria

SQLModel must not expand beyond a pilot until a follow-up review confirms:

- the pilot reduced duplication without hiding persistence semantics;
- Alembic migrations remained clear;
- tests and typing stayed stable;
- agents did not confuse SQLModel entities with API response contracts;
- the human release owner approves any broader adoption.

## Consequences

### Benefits

- Avoids destabilizing the existing backend during release stabilization.
- Keeps current repository patterns predictable for agents and reviewers.
- Allows a future experiment in a low-blast-radius module.
- Preserves explicit migrations and API-contract control.

### Costs

- Existing duplication between database rows, service types, and API models
  remains for now.
- Any SQLModel evaluation must wait for a dedicated implementation mission.
- Future contributors must continue using the existing SQLAlchemy Core pattern
  unless told otherwise.

## Review checklist for future SQLModel PRs

- [ ] The issue explicitly authorizes SQLModel.
- [ ] Existing repositories are not broadly rewritten.
- [ ] Alembic migration upgrade/downgrade paths are explicit.
- [ ] API response contracts remain intentional and tested.
- [ ] The dependency impact is documented.
- [ ] Tests cover validation, persistence, and serialization.
- [ ] PR body includes tradeoffs and a rollback path.
