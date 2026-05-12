# Skill: Hand Off Tomorrowland Work

Invoke this when transferring ownership or ending an agent session.

## Steps

1. Summarize what was completed and what remains.
2. List tests executed and their results.
3. Record context accounting:
   - `Context Loaded`
   - `Context Skipped`
   - `Token Efficiency Notes`
4. List risks and open questions.
5. Suggest concrete next steps with owner, branch, and issue.
6. Post the handoff on the PR or issue using the template from
   `docs/agents/templates.md`.

## Required fields

Every handoff must include:

```md
## Agent Handoff
### Completed
- ...
### Remaining
- ...
### Tests Executed
- ...
### Context Loaded
- ...
### Context Skipped
- ...
### Token Efficiency Notes
- Used `rg` before opening files: yes/no
- Read more than one plan: yes/no, reason
- Read broad source areas: yes/no, reason
### Risks
- ...
### Suggested Next Steps
- ...
```

## Stop conditions

- Do not hand off if CI is failing on the branch; fix or document the blocker
  first.
- Do not hand off if shared-file conflicts with another active PR are unresolved.
- Do not hand off without a concrete next action and owner.
