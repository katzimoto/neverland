# Skill: Validate a Tomorrowland Release

Invoke this when validating a release artifact or air-gapped deployment.

## Steps

1. Verify required assets exist:
   ```
   tomorrowland-release-<version>.tar.gz
   tomorrowland-release-<version>.tar.gz.sha256
   tomorrowland-images-<version>.tar.part-*
   tomorrowland-images-<version>.tar.parts.sha256
   ```
2. Verify checksums:
   ```bash
   sha256sum -c tomorrowland-release-<version>.tar.gz.sha256
   sha256sum -c tomorrowland-images-<version>.tar.parts.sha256
   ```
3. Extract and validate:
   ```bash
   tar xzf tomorrowland-release-<version>.tar.gz
   cd tomorrowland-release-<version>
   ./scripts/tomorrowland-airgap.sh validate --load-images
   ```
4. Verify no build steps in air-gapped compose:
   ```bash
   grep -Eq '^[[:space:]]+build:' docker-compose.airgap.yml && exit 1 || echo "OK"
   ```
5. Start and health-check:
   ```bash
   ./scripts/tomorrowland-airgap.sh up
   ./scripts/tomorrowland-airgap.sh status
   ```
6. Confirm Ollama model bundle is optional; missing bundle should not block startup.

## Stop conditions

- Stop if checksums fail. Do not proceed with a corrupted artifact.
- Stop if `docker-compose.airgap.yml` contains build steps.
- Stop if validation fails; debug first, then retry.
- Do not close the release issue until all steps pass and results are posted.
