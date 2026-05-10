#!/usr/bin/env bash
set -Eeuo pipefail

log() { printf '[load-airgap-images] %s\n' "$*"; }
fail() { printf '[load-airgap-images] ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'USAGE'
Usage: scripts/load-airgap-images.sh [artifact-directory]

Load the Neverland offline Docker image bundle from images/neverland-images.tar.
Run this on the air-gapped host after extracting the release archive.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

artifact_dir="${1:-$(pwd)}"
image_tar="${artifact_dir}/images/neverland-images.tar"

command -v docker >/dev/null 2>&1 || fail "docker is required to load images"
[[ -d "$artifact_dir" ]] || fail "artifact directory not found: $artifact_dir"
[[ -f "$image_tar" ]] || fail "image bundle not found: $image_tar"

log "Loading Docker images from $image_tar"
docker load -i "$image_tar"
log "Docker image load complete"

if [[ -f "${artifact_dir}/docker-compose.airgap.yml" ]]; then
  log "Images required by docker-compose.airgap.yml:"
  if docker compose --env-file "${artifact_dir}/.env.airgap.example" \
      -f "${artifact_dir}/docker-compose.airgap.yml" config --images >/tmp/neverland-airgap-images.$$ 2>/tmp/neverland-airgap-images.err.$$; then
    while IFS= read -r image; do
      [[ -n "$image" ]] || continue
      if docker image inspect "$image" >/dev/null 2>&1; then
        printf '  ok  %s\n' "$image"
      else
        printf '  missing after load  %s\n' "$image"
      fi
    done < /tmp/neverland-airgap-images.$$
    rm -f /tmp/neverland-airgap-images.$$ /tmp/neverland-airgap-images.err.$$
  else
    log "Could not render compose image list; run validate-airgap-artifact.sh for details"
    rm -f /tmp/neverland-airgap-images.$$ /tmp/neverland-airgap-images.err.$$
  fi
fi
