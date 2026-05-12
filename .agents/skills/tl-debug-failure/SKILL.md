# Skill: Debug a Failure in Tomorrowland

Invoke this when a test, workflow, or deployment is failing and you need to
isolate the root cause.

## Steps

1. Reproduce the failure locally if possible. Use the narrowest command:
   ```bash
   pytest tests/unit/test_<area>.py -q
   npx vitest run src/path/to/file.test.tsx
   ```
2. Inspect the exact error message and stack trace.
3. Check recent changes with `git log --oneline -10` and `git diff HEAD~1`.
4. Use `rg` to find related code, tests, or config.
5. Isolate the root cause before writing a fix.
6. Write the minimal fix. Do not refactor unrelated code.
7. Re-run the failing check plus broader related checks.
8. Document the triage in the issue or PR comment:
   ```
   Failing workflow:
   Failing job:
   Failing step:
   Exact command:
   Exact error:
   Likely root cause:
   Files involved:
   Minimal fix:
   Validation command:
   ```

## Stop conditions

- Stop if the failure is in a workflow you cannot reproduce locally; request
  logs instead.
- Stop if the root cause points to a design flaw; escalate to planning instead
  of patching.
- Stop if the fix would require changing shared files owned by another active PR.
