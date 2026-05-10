#!/usr/bin/env bash
set -Eeuo pipefail

log() { printf '[release-artifact] %s\n' "$*"; }
fail() { printf '[release-artifact] ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'USAGE'
Usage: scripts/build-release-artifact.sh [version]

Build first-party Neverland images, pull third-party runtime images, save an
offline Docker image bundle, and package a versioned air-gapped release archive.

Environment:
  RELEASE_DIST_DIR   Output directory for release folders and archives (default: dist)
  SKIP_DOCKER_BUILD  Set to 1 to skip docker build/pull/save for static packaging tests
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

command -v tar >/dev/null 2>&1 || fail "tar is required"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

version="${1:-${RELEASE_VERSION:-}}"
if [[ -z "$version" ]]; then
  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    version="$(git describe --tags --always --dirty 2>/dev/null || git rev-parse --short HEAD)"
  else
    version="manual"
  fi
fi
safe_version="${version//\//-}"
dist_dir="${RELEASE_DIST_DIR:-dist}"
release_name="neverland-release-${safe_version}"
release_dir="${dist_dir}/${release_name}"
archive_path="${dist_dir}/${release_name}.tar.gz"

backend_version_image="neverland/backend:${safe_version}"
frontend_version_image="neverland/frontend:${safe_version}"
backend_airgap_image="neverland/backend:airgap"
frontend_airgap_image="neverland/frontend:airgap"
third_party_images=(
  "postgres:16-alpine"
  "redpandadata/redpanda:v24.1.9"
  "docker.elastic.co/elasticsearch/elasticsearch:8.14.3"
  "qdrant/qdrant:v1.10.1"
  "libretranslate/libretranslate:latest"
  "ollama/ollama:latest"
)
all_images=(
  "$backend_airgap_image"
  "$frontend_airgap_image"
  "$backend_version_image"
  "$frontend_version_image"
  "${third_party_images[@]}"
)

required_files=(
  "docker-compose.yml"
  "docker-compose.airgap.yml"
  ".env.airgap.example"
  "scripts/load-airgap-images.sh"
  "scripts/validate-airgap-artifact.sh"
  "docs/operations/air-gapped-deployment.md"
  "docs/operations/production-compose.md"
)
for file in "${required_files[@]}"; do
  [[ -f "$file" ]] || fail "required packaging input is missing: $file"
done

rm -rf "$release_dir" "$archive_path"
mkdir -p "$release_dir/images" "$release_dir/scripts" "$release_dir/docs"

if [[ "${SKIP_DOCKER_BUILD:-0}" != "1" ]]; then
  command -v docker >/dev/null 2>&1 || fail "docker is required unless SKIP_DOCKER_BUILD=1"
  log "Building first-party backend image: $backend_version_image and $backend_airgap_image"
  docker build -f docker/backend.Dockerfile \
    --build-arg "APP_VERSION=${version}" \
    -t "$backend_version_image" \
    -t "$backend_airgap_image" \
    .

  log "Building first-party frontend image: $frontend_version_image and $frontend_airgap_image"
  docker build -f docker/frontend.Dockerfile \
    --build-arg "APP_VERSION=${version}" \
    -t "$frontend_version_image" \
    -t "$frontend_airgap_image" \
    .

  for image in "${third_party_images[@]}"; do
    log "Pulling third-party runtime image: $image"
    docker pull "$image"
  done

  log "Saving offline image bundle"
  docker save -o "$release_dir/images/neverland-images.tar" "${all_images[@]}"
else
  log "SKIP_DOCKER_BUILD=1 set; writing placeholder image bundle for static packaging only"
  printf 'placeholder; not a docker image bundle\n' > "$release_dir/images/neverland-images.tar"
fi

cp docker-compose.yml "$release_dir/docker-compose.yml"
cp docker-compose.airgap.yml "$release_dir/docker-compose.airgap.yml"
sed \
  -e "s/^APP_VERSION=.*/APP_VERSION=${safe_version}/" \
  -e "s|^NEVERLAND_BACKEND_IMAGE=.*|NEVERLAND_BACKEND_IMAGE=${backend_airgap_image}|" \
  -e "s|^NEVERLAND_FRONTEND_IMAGE=.*|NEVERLAND_FRONTEND_IMAGE=${frontend_airgap_image}|" \
  .env.airgap.example > "$release_dir/.env.airgap.example"
cp scripts/load-airgap-images.sh "$release_dir/scripts/load-airgap-images.sh"
cp scripts/validate-airgap-artifact.sh "$release_dir/scripts/validate-airgap-artifact.sh"
chmod +x "$release_dir/scripts/load-airgap-images.sh" "$release_dir/scripts/validate-airgap-artifact.sh"
cp docs/operations/air-gapped-deployment.md "$release_dir/docs/air-gapped-deployment.md"
cp docs/operations/production-compose.md "$release_dir/docs/production-compose.md"

{
  printf 'Neverland release artifact %s\n\n' "$version"
  printf 'Images included in images/neverland-images.tar:\n'
  printf -- '- %s\n' "${all_images[@]}"
  printf '\nStart command:\n'
  printf 'docker compose --env-file .env -f docker-compose.airgap.yml up -d\n'
} > "$release_dir/README-airgap.txt"

(
  cd "$release_dir"
  sha256sum \
    docker-compose.yml \
    docker-compose.airgap.yml \
    .env.airgap.example \
    images/neverland-images.tar \
    scripts/load-airgap-images.sh \
    scripts/validate-airgap-artifact.sh \
    docs/air-gapped-deployment.md \
    docs/production-compose.md \
    README-airgap.txt > checksums.txt
)

log "Creating archive: $archive_path"
mkdir -p "$dist_dir"
tar -C "$dist_dir" -czf "$archive_path" "$release_name"
(
  cd "$dist_dir"
  sha256sum "${release_name}.tar.gz" > "${release_name}.tar.gz.sha256"
)

log "Release artifact created: $archive_path"
log "Archive checksum: ${archive_path}.sha256"
