# Skill: Implement a Tomorrowland Issue

Invoke this after planning is complete and you have claimed the issue.

## Steps

1. Create a branch: `issue/<number>-<short-name>`.
2. Run the narrowest existing tests that cover the area to confirm baseline passes.
3. Make the smallest change that satisfies the acceptance criteria.
4. Add or update tests to prove the change.
5. Run checks in order:
   ```bash
   ruff check --fix src/ tests/ migrations/
   ruff format src/ tests/ migrations/
   mypy src --strict
   pytest tests/unit/test_<area>.py -q
   pytest tests/integration/test_<area>.py -q
   ```
6. If frontend is touched:
   ```bash
   npm --prefix frontend run lint
   npm --prefix frontend run typecheck
   npm --prefix frontend run test
   npm --prefix frontend run build
   ```
7. Update `CHANGELOG.md` if the change is user-visible.
8. Commit with a concise message focused on the "why".
9. Push and open a PR referencing the issue.

## Constraints

- Do not mix release blockers, architecture planning, UI polish, or docs cleanup
  in the same PR.
- Do not introduce SQLModel or refactor repositories broadly unless explicitly
  authorized.
- Do not bypass auth, permission, feature-flag, or safe download patterns.
- Every migration needs upgrade and downgrade.

## Stop conditions

- Stop if implementation requires changing files outside `Allowed Changes`.
- Stop if you discover a need to change shared files owned by another active PR.
- Stop if the issue scope expands beyond the original objective; open a follow-up
  issue instead.
