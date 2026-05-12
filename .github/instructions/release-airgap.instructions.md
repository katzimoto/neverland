---
applyTo: "scripts/**/*,.github/workflows/**/*,docker-compose*.yml,Dockerfile*,README-airgap.md,docs/operations/**/*.md"
---

# Release and air-gapped instructions

Follow `AGENTS.md` first. These rules apply when touching release tooling,
workflows, Compose files, Dockerfiles, scripts, and operations docs.

## Release guardrails

- Preserve air-gapped runtime behavior. Operators should not need internet access
  or image builds on the target host when using release artifacts.
- Never use or recommend `docker compose down -v` for upgrades; it deletes
  persistent product data volumes.
- Keep release blockers isolated from optional features and UI polish.
- Do not close release issues until artifacts, checksums, validation results, and
  final release URLs are posted.
- Inspect failing workflow logs before patching scripts or workflows.

## Assets and artifacts

Expected air-gapped release assets use Tomorrowland names:

```text
tomorrowland-release-<version>.tar.gz
tomorrowland-release-<version>.tar.gz.sha256
tomorrowland-images-<version>.tar.part-*
tomorrowland-images-<version>.tar.parts.sha256
```

Optional Ollama model bundles must remain optional add-ons unless the release
issue explicitly changes the policy.

## Validation

Prefer exact validation commands in the issue or PR. Common commands include:

```bash
docker compose config
./scripts/tomorrowland-airgap.sh validate --load-images
./scripts/tomorrowland-airgap.sh status
```

For workflow failures, include this triage in the PR or issue comment:

```text
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
