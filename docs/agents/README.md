# Agent Instructions

Use GitHub Issues and PRs as the current source of truth for Tomorrowland work.
Historical phase plans are useful context only when an issue asks for them.

## Practical workflow

1. Read `AGENTS.md` first, then `docs/agents/token-efficiency.md` for any
   non-trivial task.
2. If using GitHub Copilot, also read `.github/copilot-instructions.md` and the
   relevant path-specific instruction file under `.github/instructions/`.
3. If using OpenCode, also read `docs/agents/opencode.md`; project-level
   OpenCode instructions are configured in `opencode.json`.
4. Read the issue body before source files. Follow its context budget, allowed
   paths, forbidden paths, and acceptance criteria.
5. Keep context narrow. Use `rg` and `rg --files` before opening files.
6. Do not edit `spec.md` or `spec-v4.pdf` unless the user explicitly asks.
7. Keep release blockers isolated from optional features, UI polish, and future
   planning work.
8. Do not mix release management, architecture planning, implementation, and
   optional PR work in one PR.
9. End changed-file runs with a clear handoff: completed work, remaining work,
   tests, context loaded/skipped, risks, and next steps.

## Role routing

- Use Claude Code for planning, architecture review, security/edge cases, broad
  localization/UX consistency, docs polish, issue decomposition, and reviewer
  reports.
- Use Codex for scoped implementation after a plan, mechanical refactors,
  targeted tests, lint/type/build fixes, scripts, and CI repair.
- Use GitHub Copilot for in-editor implementation help, narrow issue execution,
  repetitive refactors, targeted tests, PR summaries, and additional code review
  comments.
- Use OpenCode for local repository coding loops, bounded implementation,
  targeted tests, mechanical refactors, and failure repair when the issue scope is
  already clear.
- Human reviewers own priority changes, merge decisions, risky migrations,
  destructive-operation policy, and canonical requirement changes.

## Copilot

- [Copilot workflow](copilot.md) — how to route Tomorrowland work to Copilot,
  which prompts to use, and when to escalate to Codex, Claude, OpenCode, or a
  human.

## OpenCode

- [OpenCode workflow](opencode.md) — how to route Tomorrowland work to OpenCode,
  which prompts to use, and when to escalate to Copilot, Codex, Claude, or a
  human.

## Reusable Skills

Reusable workflow skills live under `.agents/skills/` for all agents:

- `tl-plan-issue` — planning workflow before touching code
- `tl-implement-issue` — implementation workflow after planning
- `tl-review-pr` — PR review workflow
- `tl-debug-failure` — debug triage workflow
- `tl-release-check` — release artifact validation workflow
- `tl-handoff` — ownership transfer and session handoff workflow

Invoke the relevant skill at the start of a mission instead of re-reading the
full `AGENTS.md`.
