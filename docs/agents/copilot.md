# GitHub Copilot workflow

Use GitHub Copilot as an implementation accelerator and review assistant for
Tomorrowland. Do not use it as the source of truth for project priority,
architecture, release policy, security posture, or merge decisions.

## What Copilot should do

Good Copilot missions:

- Add or update narrowly scoped tests.
- Implement a small issue after the issue defines allowed paths and acceptance
  criteria.
- Refactor repetitive code inside one bounded module.
- Repair lint, typecheck, or build failures after the failing output is known.
- Summarize a PR and call out obvious review risks.
- Review a PR for correctness, regressions, permission mistakes, and missing
  tests.

Avoid giving Copilot broad missions such as "improve the app", "clean up the
backend", "redesign the UI", "make release ready", or "fix security". Convert
broad work into GitHub Issues first.

## Recommended issue shape

Use the mission issue template and include:

- One objective.
- Context budget.
- Allowed source paths.
- Allowed test paths.
- Explicit forbidden paths.
- Acceptance criteria.
- Validation commands.

Copilot performs better when the issue tells it exactly which files it may inspect
and what counts as done.

## Recommended prompts

For implementation:

```text
Use this issue as the source of truth. Read AGENTS.md, docs/agents/token-efficiency.md,
.github/copilot-instructions.md, and only the allowed paths listed in the issue.
Make the smallest code change that satisfies the acceptance criteria. Open a PR
with the standard handoff and list the checks you ran.
```

For test generation:

```text
Add targeted tests for the behavior described in this issue. Do not change
production code unless a failing test proves a bug and the issue allows it.
Explain the exact behavior covered by each new test.
```

For PR review:

```text
Review this PR against the linked issue, AGENTS.md, and .github/copilot-instructions.md.
Focus on correctness, security/permissions, regression risk, test gaps, and
scope creep. Ignore style-only comments unless they block maintainability.
```

For CI repair:

```text
Use the failing job logs as the source of truth. Identify the failing workflow,
job, step, exact command, exact error, likely root cause, minimal fix, and
validation command before editing files.
```

## Routing with other agents

- Use Copilot for small implementation, repetitive edits, local coding help,
  targeted tests, and PR review assistance.
- Use Codex for mechanical repository-wide execution, larger scoped
  implementation, and CI repair where branch-level changes are needed.
- Use Claude for architecture, security, migrations, edge cases, issue
  decomposition, and broad review.
- Use a human reviewer for priority changes, canonical requirements, release
  decisions, destructive-operation policy, and merges.

## Done criteria for Copilot PRs

A Copilot PR is ready for human/Claude review only when:

- The PR references exactly one issue or named subtask.
- The changed files stay inside the allowed scope.
- Tests/checks are listed, or skipped checks are justified.
- The PR body includes the standard agent handoff.
- Risks and follow-ups are explicit.
