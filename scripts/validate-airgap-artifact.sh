#!/usr/bin/env bash
set -Eeuo pipefail

log() { printf '[validate-airgap-artifact] %s\n' "$*"; }
fail() { printf '[validate-airgap-artifact] ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'USAGE'
Usage: scripts/validate-airgap-artifact.sh [--load-images] [artifact-directory]

Validate an extracted Neverland air-gapped release artifact.
Checks required files, checksums, compose rendering, forbidden build steps, and
that every image referenced by docker-compose.airgap.yml exists in the offline
Docker image bundle. With --load-images, also docker-loads the bundle and verifies
image presence in the local Docker daemon.
USAGE
}

load_images=0
artifact_dir="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --load-images)
      load_images=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      artifact_dir="$1"
      shift
      ;;
  esac
done

command -v docker >/dev/null 2>&1 || fail "docker with the Compose plugin is required"
command -v tar >/dev/null 2>&1 || fail "tar is required"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required"

required_files=(
  "docker-compose.yml"
  "docker-compose.airgap.yml"
  ".env.airgap.example"
  "images/neverland-images.tar"
  "scripts/load-airgap-images.sh"
  "scripts/validate-airgap-artifact.sh"
  "scripts/preflight-upgrade-check.sh"
  "scripts/backup-airgap-data.sh"
  "scripts/restore-airgap-data.sh"
  "scripts/upgrade-airgap.sh"
  "docs/air-gapped-deployment.md"
  "docs/air-gapped-upgrade.md"
  "release-manifest.json"
  "docs/production-compose.md"
  "checksums.txt"
)

[[ -d "$artifact_dir" ]] || fail "artifact directory not found: $artifact_dir"
cd "$artifact_dir"

for file in "${required_files[@]}"; do
  [[ -f "$file" ]] || fail "required file is missing: $file"
done
log "Required files are present"

sha256sum -c checksums.txt
log "Checksums are valid"

for key in release_version git_commit created_at images compose_files minimum_docker_version minimum_compose_version migrations persistent_data backup_restore_script_version; do
  if ! grep -Eq "\"${key}\"[[:space:]]*:" release-manifest.json; then
    fail "release-manifest.json is missing required key: $key"
  fi
done
log "Release manifest includes required upgrade safety keys"

tmp_dir="$(mktemp -d)"
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

if ! docker compose --env-file .env.airgap.example -f docker-compose.airgap.yml config > "$tmp_dir/compose.rendered.yml"; then
  fail "docker compose config failed for docker-compose.airgap.yml"
fi
log "docker compose config passed"

if grep -Eq '^[[:space:]]+build:' "$tmp_dir/compose.rendered.yml" docker-compose.airgap.yml; then
  fail "air-gapped compose configuration must not contain build steps"
fi
log "No build steps are present in the air-gapped compose configuration"

if ! docker compose --env-file .env.airgap.example -f docker-compose.airgap.yml config --images > "$tmp_dir/compose-images.txt"; then
  fail "could not list compose images"
fi

if [[ ! -s "$tmp_dir/compose-images.txt" ]]; then
  fail "compose image list is empty"
fi

if ! tar -tf images/neverland-images.tar >/dev/null; then
  fail "image bundle is not a readable tar archive: images/neverland-images.tar"
fi
if ! tar -xOf images/neverland-images.tar manifest.json > "$tmp_dir/manifest.json"; then
  fail "image bundle does not contain Docker manifest.json"
fi

missing=0
while IFS= read -r image; do
  [[ -n "$image" ]] || continue
  if grep -Fq "\"$image\"" "$tmp_dir/manifest.json"; then
    printf '  bundled  %s\n' "$image"
  else
    printf '  missing  %s\n' "$image" >&2
    missing=1
  fi
done < "$tmp_dir/compose-images.txt"
[[ "$missing" -eq 0 ]] || fail "one or more compose images are missing from images/neverland-images.tar"
log "Every compose image is present in the offline image bundle"

if [[ "$load_images" -eq 1 ]]; then
  log "Loading image bundle into local Docker daemon for verification"
  docker load -i images/neverland-images.tar
  while IFS= read -r image; do
    [[ -n "$image" ]] || continue
    docker image inspect "$image" >/dev/null || fail "loaded Docker daemon is missing image: $image"
  done < "$tmp_dir/compose-images.txt"
  log "Loaded images are available locally"
fi

log "Air-gapped artifact validation passed"
