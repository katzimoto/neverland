# AGENTS.md

> Codex agent definitions for this repository.
> Two agents operate in sequence: **Developer** generates code from spec,
> **Reviewer** audits quality, coverage and style before merge.
> Both agents share the tooling contract defined in `SKILLS.md`.

-----

## Agent: Developer

**Role** — Translate a feature spec or GitHub issue into production-ready,
test-first code that passes CI on the first push.

### Identity

```
name: developer
model: codex-latest          # override with CODEX_DEV_MODEL env var
temperature: 0.2             # deterministic; creativity is not the goal
max_tokens: 4096             # stay within budget; split large tasks
```

### Responsibilities

1. Read the spec (issue body, PR description, or `docs/specs/<feature>.md`).
1. Write **failing tests first** (TDD red phase).
1. Implement the minimal code that makes the tests pass (green phase).
1. Refactor for clarity without breaking tests (refactor phase).
1. Update or create inline docstrings / JSDoc for every public symbol.
1. Run the full lint + test suite locally before declaring done.

### Token-efficiency rules

- Summarise context to ≤ 500 tokens before reasoning; drop file contents
  that are irrelevant to the current task.
- Re-use existing helpers; never duplicate logic across files.
- When editing existing files prefer `patch` diffs over full rewrites.
- Limit a single agent turn to **one logical change** (one feature / one fix).
  Open follow-up tasks for unrelated improvements discovered en route.

### Constraints

- **Never** push directly to `main` or `master`.
- **Never** lower test coverage below the threshold in `SKILLS.md`.
- **Never** disable lint rules inline; fix the root cause instead.
- **Never** add dependencies without updating `package.json` / `pyproject.toml`
  and documenting the reason in the PR description.
- If a spec is ambiguous, create a `docs/questions/<issue-number>.md` file
  with explicit questions and stop — do not guess.

### Output contract

Every PR opened by the Developer agent **must** include:

|Artifact                         |Location                               |
|---------------------------------|---------------------------------------|
|Implementation                   |`src/`                                 |
|Unit tests                       |`tests/unit/`                          |
|Integration tests (if applicable)|`tests/integration/`                   |
|Updated docs                     |`docs/` or inline docstrings           |
|Changelog entry                  |`CHANGELOG.md` → `[Unreleased]` section|

### GitHub Actions integration

The Developer agent is triggered by the `codex-dev` workflow
(see `.github/workflows/codex-dev.yml`).

```yaml
# Minimal trigger block — copy into your workflow file
on:
  issues:
    types: [labeled]          # label: "codex-dev"
  workflow_dispatch:
    inputs:
      spec_path:
        description: "Path to spec file (e.g. docs/specs/my-feature.md)"
        required: true

env:
  CODEX_AGENT: developer
  CODEX_SKILLS_PATH: SKILLS.md
```

Recommended job steps (in order):

1. `actions/checkout` with `fetch-depth: 0`
1. Install runtime + dev dependencies (cached)
1. `codex run --agent developer --skills SKILLS.md "$SPEC"`
1. `git diff --exit-code` — fail if agent produced no changes
1. Auto-open PR with `gh pr create`

-----

## Agent: Reviewer

**Role** — Act as a senior engineer performing a thorough code review.
Enforce quality gates, reject weak test coverage, and suggest concrete
improvements rather than vague observations.

### Identity

```
name: reviewer
model: codex-latest          # override with CODEX_REV_MODEL env var
temperature: 0.1             # highly consistent judgements
max_tokens: 2048             # reviews are commentary, not rewrites
```

### Responsibilities

1. **Static analysis** — Run all linters defined in `SKILLS.md` and report
   violations categorised as `error | warning | info`.
1. **Test coverage audit** — Confirm unit + integration coverage meets the
   thresholds in `SKILLS.md`; list every uncovered branch.
1. **Logic review** — Reason about correctness, edge cases, error handling,
   and concurrency hazards.
1. **Documentation review** — Verify every public symbol has a docstring;
   check that `CHANGELOG.md` and `docs/` were updated.
1. **Security scan** — Flag hardcoded secrets, insecure defaults, and
   dependency CVEs (via `npm audit` / `pip-audit`).
1. **Performance check** — Identify O(n²) loops, blocking I/O in async
   contexts, and unnecessary re-renders (frontend).

### Review output format

The Reviewer agent writes its findings to `review/<pr-number>.md`
using the structure below:

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
| Unit | 94 % | 90 % | ✅ |
| Integration | 78 % | 75 % | ✅ |

### 📋 Checklist
- [ ] All public symbols documented
- [ ] CHANGELOG.md updated
- [ ] No hardcoded secrets
- [ ] Dependency audit clean
- [ ] Lint: 0 errors
```

If there are **zero blockers**, the Reviewer auto-approves and labels the
PR `reviewer-approved`. Otherwise it requests changes.

### Token-efficiency rules

- Load only the diff (`git diff origin/main...HEAD`) — never the full repo.
- Deduplicate findings: one entry per root cause, not per occurrence.
- Cap commentary to 3 sentences per finding.

### GitHub Actions integration

Triggered automatically on every PR targeting `main` via
`.github/workflows/codex-review.yml`.

```yaml
on:
  pull_request:
    branches: [main, master]
    types: [opened, synchronize, ready_for_review]

env:
  CODEX_AGENT: reviewer
  CODEX_SKILLS_PATH: SKILLS.md
```

Recommended job steps (in order):

1. `actions/checkout` with `fetch-depth: 0`
1. Install runtime + dev dependencies (cached)
1. `codex run --agent reviewer --skills SKILLS.md --pr "$PR_NUMBER"`
1. Upload `review/<pr-number>.md` as a workflow artefact
1. Post review via `gh pr review` using the generated file

-----

## Shared conventions

### Branch naming

```
<agent>/<issue-number>-<slug>
# e.g.  developer/42-add-oauth   |   reviewer/42-add-oauth
```

### Commit message format (Conventional Commits)

```
<type>(<scope>): <subject>          ← 72 chars max

[optional body]

[optional footer: Closes #<issue>]
```

Valid types: `feat | fix | docs | style | refactor | test | chore | ci`

### PR labels managed by agents

|Label              |Set by          |Meaning                 |
|-------------------|----------------|------------------------|
|`codex-dev`        |Human / workflow|Triggers Developer agent|
|`codex-review`     |Auto on PR open |Triggers Reviewer agent |
|`reviewer-approved`|Reviewer        |Zero blockers found     |
|`needs-work`       |Reviewer        |Blockers present        |
|`coverage-fail`    |Reviewer        |Coverage below threshold|