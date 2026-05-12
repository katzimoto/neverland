# Skill: Plan a Tomorrowland Issue

Invoke this when you are about to start work on a GitHub Issue and need a
focused plan before touching code.

## Steps

1. Read the issue body, especially `Context Budget`, `Allowed Changes`, and
   `Forbidden Changes`.
2. Load context in this order:
   - `AGENTS.md`
   - `docs/agents/token-efficiency.md`
   - `CLAUDE.md` (Claude Code only)
   - One relevant `docs/context/<area>.md` when needed
   - The single implementation/design plan referenced by the issue, if any
3. Search for existing code with `rg` before opening large files.
4. Identify risks: shared files, migrations, release blockers, security boundaries.
5. Draft a plan comment on the issue with:
   - Approach
   - Files expected to change
   - Tests expected to add/update
   - Risks and mitigations
6. Post the Agent Claim template from `docs/agents/templates.md`.
7. Wait for human or lead-agent approval if the issue is `risk:high` or a release
   blocker.

## Stop conditions

- Stop if the issue lacks a clear context budget and scope cannot be inferred.
- Stop if `spec.md` or `spec-v4.pdf` appears necessary but was not explicitly
  authorized.
- Stop if two active missions need the same shared files.
