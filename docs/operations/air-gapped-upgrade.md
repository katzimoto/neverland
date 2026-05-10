# Air-Gapped Upgrade Without Data Loss

This guide explains how to upgrade an existing air-gapped Neverland deployment
with a newer release artifact while preserving operator configuration and
persistent product data.

> **Never run `docker compose down -v` during an upgrade.** The `-v` flag deletes
> named volumes, including PostgreSQL, Elasticsearch, Qdrant, files, model, and
> broker data.

The upgrade invariant is simple: **replace images and run migrations; never
replace, delete, or recreate data volumes by default.**

## Prerequisites

- An existing Neverland air-gapped deployment directory containing `.env` and the
  active Compose file, usually `docker-compose.airgap.yml`.
- Docker Engine and Docker Compose plugin already installed on the target host.
  The release manifest declares the minimum expected versions.
- A newer extracted `neverland-release-<version>/` artifact copied to the
  air-gapped host.
- Enough free disk space for:
  - the new image bundle,
  - a PostgreSQL dump,
  - a files volume archive,
  - optional storage-level snapshots of Elasticsearch and Qdrant volumes.
- A maintenance window. Database migrations run before the upgraded API starts.

Do not perform the upgrade from inside a fresh artifact directory unless that is
also the long-lived deployment directory that contains the current `.env` and
volumes. Most operators should run upgrade commands from the existing deployment
directory and pass `--artifact-dir ../neverland-release-<version>`.

## What data is preserved

The upgrade scripts preserve Docker volumes and operator configuration by
default. This includes:

- PostgreSQL metadata and application data: users, groups, permissions, source
  connector configuration, LDAP-related configuration, documents metadata,
  comments, annotations, subscriptions, notifications, activity, translations,
  summaries, entities, tags, DLQ, and audit records.
- `files_data`, containing ingested files and document storage under `FILES_ROOT`.
- Elasticsearch index data in `elasticsearch_data`.
- Qdrant vector data in `qdrant_data`.
- Redpanda/Kafka data in `kafka_data`.
- LibreTranslate and Ollama volumes.
- Optional monitoring data when the operator backs up monitoring volumes.
- `.env` and local Compose overrides.

The scripts do not intentionally delete or recreate these volumes.

## What the backup script captures

`scripts/backup-airgap-data.sh` (from the newer release artifact, or from the deployment directory after an upgrade installs helper scripts) creates a timestamped directory under `backups/`
by default. It captures:

- `.env`.
- Active Compose files and local override files.
- Rendered Compose configuration, image references, service state, Docker
  version, Compose version, and current volumes metadata.
- A PostgreSQL custom-format dump from the running `postgres` service.
- A compressed archive of the `files_data` named volume.
- Notes describing safe Elasticsearch and Qdrant backup/restore strategy.
- Notes for optional monitoring data if a monitoring profile or override exists.

Elasticsearch and Qdrant live snapshot repositories are deployment-specific, so
the script does not attempt to configure them automatically. For high-risk
upgrades, stop services without deleting volumes and take storage-level snapshots
or offline archives of `elasticsearch_data` and `qdrant_data` before continuing.

## Required commands before upgrade

On the connected machine, verify the downloaded archive checksum before moving it
to the air-gapped host:

```bash
sha256sum -c neverland-release-<version>.tar.gz.sha256
```

On the air-gapped host, extract the release artifact near the deployment
directory:

```bash
tar xzf neverland-release-<version>.tar.gz
```

From the existing deployment directory, confirm `.env` still contains the current
operator settings. The upgrade flow never overwrites `.env` automatically.

## Artifact checksum verification

If `checksums.txt` is present in the extracted artifact, the preflight script
verifies it. You can also verify manually:

```bash
cd neverland-release-<version>
sha256sum -c checksums.txt
```

## Preflight command

Run preflight from the existing deployment directory:

```bash
../neverland-release-<version>/scripts/preflight-upgrade-check.sh --artifact-dir ../neverland-release-<version>
```

The preflight check is read-only. It validates the deployment directory, `.env`,
Compose files, Docker Engine, Docker Compose plugin, current service state,
current image tags, expected persistent volume names, configured folder-source
host path existence, artifact checksums, required artifact files,
`release-manifest.json`, air-gapped Compose rendering, absence of required
`build:` steps, and that every image referenced by the artifact Compose file is
bundled or already present locally. Artifact validation also rejects obvious
non-placeholder secrets in packaged environment templates.

Stop and resolve any preflight failure before continuing.

## Backup command

Create a backup from the existing deployment directory:

```bash
../neverland-release-<version>/scripts/backup-airgap-data.sh --output-dir ./backups
```

The backup script fails closed: if PostgreSQL dumping or files archiving fails,
the script exits non-zero and leaves a partial backup marked with `FAILED.txt`
for inspection. Do not proceed with the upgrade until a complete backup contains
`SUCCESS.txt`.

For Elasticsearch and Qdrant, use the backup notes as the safe fallback:

```bash
docker compose --env-file .env -f docker-compose.airgap.yml stop
# take storage-level snapshots or offline archives of elasticsearch_data and qdrant_data
docker compose --env-file .env -f docker-compose.airgap.yml up -d
```

Do not add `-v` to any Compose stop or down command.

## Image loading command

The upgrade orchestrator loads images automatically, but you can load them
manually when validating an artifact:

```bash
bash ../neverland-release-<version>/scripts/load-airgap-images.sh ../neverland-release-<version>
```

This uses only `images/neverland-images.tar` from the release artifact. It does
not pull from the internet and does not build images on the target host.

## Upgrade command

From the existing deployment directory:

```bash
../neverland-release-<version>/scripts/upgrade-airgap.sh --artifact-dir ../neverland-release-<version>
```

The orchestrator performs the following steps:

1. Runs the read-only preflight check.
2. Runs `scripts/backup-airgap-data.sh` unless `--skip-backup` is explicitly
   provided.
3. Loads images from the local release artifact.
4. Verifies every expected image tag exists locally.
5. Copies the new release Compose files into the deployment directory while
   preserving `.env`.
6. Stops services with `docker compose stop`, preserving all volumes.
7. Starts PostgreSQL and runs the `migrate` service/job.
8. Stops immediately if migrations fail.
9. Starts the upgraded stack.
10. Runs basic `/health` checks when `curl` is available.

Use `--skip-backup` only when you have already created and verified an equivalent
backup outside this script:

```bash
../neverland-release-<version>/scripts/upgrade-airgap.sh --artifact-dir ../neverland-release-<version> --skip-backup
```

## Migration behavior

The air-gapped Compose file includes a `migrate` service that runs:

```bash
alembic upgrade head
```

The upgrade script starts PostgreSQL, runs this migration job, and refuses to
start the upgraded stack if migrations fail. This prevents the API and frontend
from running against a partially migrated database.


## Host-mounted SMB shares during upgrades

Host-mounted SMB/CIFS shares are external host state; they are not packaged
inside Neverland release artifacts and are not recreated by the upgrade scripts.
If an existing deployment uses an SMB share through the `folder` connector, keep
both the host mount path, such as `/mnt/neverland-smb/legal`, and the container
path, such as `/data/smb/legal`, stable across upgrades so existing source
configuration continues to work.

Before starting the upgraded stack in the #75 upgrade flow, remount or verify the
SMB share on the host:

```bash
mount | grep /mnt/neverland-smb/legal
ls -la /mnt/neverland-smb/legal
```

Back up `/etc/fstab` or the equivalent systemd mount configuration and the
root-owned SMB credential file outside Neverland. Do not store real SMB
credentials in `.env`, release artifacts, Compose examples, documentation, or
screenshots. Do not use destructive volume commands to fix SMB mount issues;
repair the host mount, verify the `api` service bind mount, and then restart the
stack without deleting Neverland volumes.

## Post-upgrade validation checklist

Complete this checklist before declaring the upgrade successful:

- API `GET /health` responds.
- Admin `GET /admin/readiness` responds for an admin user.
- Frontend is reachable.
- Login works.
- Existing admin users and groups are visible.
- Existing source connectors are visible.
- At least one existing document can be searched.
- At least one existing document can be previewed.
- Q&A route responds if enabled.
- Comments and annotations remain visible if present.
- Subscriptions and notifications remain visible if present.
- PostgreSQL is not unexpectedly empty.
- Existing files are still present; no volume appears to have been recreated.
- Elasticsearch and Qdrant indexes are populated or rebuild behavior is understood
  and expected.

Useful commands:

```bash
docker compose --env-file .env -f docker-compose.airgap.yml ps
curl -fsS http://127.0.0.1:${API_PORT:-8000}/health
curl -fsS http://127.0.0.1:${FRONTEND_PORT:-8080}/health
```

## Restore and rollback procedure

If preflight, image loading, or backup fails, no runtime data should have changed.
Fix the failure and rerun preflight.

If migration or post-upgrade validation fails:

1. Do **not** run `docker compose down -v`.
2. Stop services without deleting volumes:

   ```bash
   docker compose --env-file .env -f docker-compose.airgap.yml stop
   ```

3. Restore the backup created before upgrade:

   ```bash
   scripts/restore-airgap-data.sh --backup-dir ./backups/neverland-airgap-backup-<timestamp> --confirm-restore
   ```

4. Restore Elasticsearch and Qdrant storage snapshots if you created them.
5. Start the restored stack:

   ```bash
   docker compose --env-file .env -f docker-compose.airgap.yml up -d
   ```

The restore script intentionally requires `--confirm-restore`. It restores `.env`,
backed-up Compose files, the PostgreSQL dump, and the `files_data` archive. It
prints warnings before replacing database and files-volume contents. It does not
automate Elasticsearch or Qdrant snapshot restore; follow the notes in the backup
directory for those volumes.

## Common failure modes

| Failure | Safe response |
| --- | --- |
| Missing `.env` | Stop. Run from the existing deployment directory or restore `.env` from backup. |
| Missing `release-manifest.json` | Stop. The artifact is not compatible with this upgrade workflow. Use a #73-style artifact. |
| Checksum failure | Stop. Re-copy or re-download the artifact from the connected environment. |
| Compose config contains `build:` | Stop. Use the air-gapped Compose file from the release artifact; do not build on the target host. |
| Image missing after load | Stop. The artifact image bundle is incomplete or failed to load. |
| PostgreSQL dump fails | Stop. Do not upgrade without a successful database backup. |
| Files archive fails | Stop. Do not upgrade without a successful files backup or equivalent storage snapshot. |
| Migration fails | Stop. Do not start the upgraded API/frontend; restore from backup or investigate migration logs. |
| Health check fails | Keep volumes intact, inspect logs, and roll back if validation cannot be completed. |

## Compatibility notes between versions

- Upgrade only with release artifacts that include `release-manifest.json`,
  `docker-compose.airgap.yml`, `images/neverland-images.tar`, checksums, and the
  upgrade scripts.
- Review `release-manifest.json` before upgrade. Confirm the expected release
  version, commit SHA, Compose files, minimum Docker and Compose versions,
  migration expectation, persistent volumes, and backup/restore script version.
- Database migrations are expected to be forward migrations. Rollback requires a
  pre-upgrade backup; do not assume database schema downgrades are available.
- If persistent volume names change in a future release, stop and perform a
  manual migration plan rather than letting Compose create new empty volumes.

## Recovering when validation fails

- Keep services stopped or running as-is; do not delete volumes.
- Save logs for review:

  ```bash
  docker compose --env-file .env -f docker-compose.airgap.yml logs --no-color > upgrade-failure.log
  ```

- Check whether the failure is configuration-only, such as a port conflict or an
  incorrect `.env` value. Correct `.env` manually; scripts never overwrite it.
- If data appears missing, assume a wrong project name or volume path before
  assuming data loss. Inspect `docker volume ls` and the backup metadata.
- If validation cannot be repaired quickly, restore the pre-upgrade backup and
  Elasticsearch/Qdrant snapshots.

## Follow-up limitation text

Elasticsearch and Qdrant snapshot automation remains deployment-specific. A
follow-up issue should add optional, operator-configured snapshot repository
support that can validate a repository path, trigger snapshots, and restore them
without storing credentials or host-specific paths in release artifacts.
