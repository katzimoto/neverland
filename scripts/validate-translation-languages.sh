#!/usr/bin/env bash
# Validate that a running LibreTranslate service supports all required
# air-gapped translation language pairs for Neverland.
#
# Usage:
#   LIBRETRANSLATE_URL=http://localhost:5000 bash scripts/validate-translation-languages.sh
#
# Exit codes:
#   0  All required language pairs are present and reachable.
#   1  One or more required pairs are missing or the service is unreachable.
#
# zt (Traditional Chinese) is optional: the script warns but does not fail if zt
# is absent from the /languages response. If zt is required for this release,
# the release owner must explicitly accept the limitation noted in the output.
set -Eeuo pipefail

LIBRETRANSLATE_URL="${LIBRETRANSLATE_URL:-http://localhost:5000}"
TIMEOUT="${VALIDATE_TIMEOUT:-15}"

log()  { printf '[validate-translation] %s\n' "$*"; }
warn() { printf '[validate-translation] WARN: %s\n' "$*" >&2; }
fail() { printf '[validate-translation] ERROR: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Check /languages endpoint
# ---------------------------------------------------------------------------
log "Checking LibreTranslate /languages at ${LIBRETRANSLATE_URL} ..."

languages_json=$(curl -fsS --max-time "${TIMEOUT}" "${LIBRETRANSLATE_URL}/languages") \
  || fail "/languages endpoint is not reachable at ${LIBRETRANSLATE_URL}"

log "/languages endpoint is reachable"

# ---------------------------------------------------------------------------
# 2. Verify required language codes are present
# ---------------------------------------------------------------------------
required_codes=(en ar fr ru es zh ko th he)

for code in "${required_codes[@]}"; do
  if ! printf '%s' "$languages_json" | grep -qF "\"code\":\"${code}\""; then
    fail "Required language code '${code}' not found in /languages response"
  fi
  log "Language code present: ${code}"
done

# zt (Traditional Chinese) is optional
zt_available=0
if printf '%s' "$languages_json" | grep -qF '"code":"zt"'; then
  log "Optional language code present: zt (Traditional Chinese)"
  zt_available=1
else
  warn "Optional language code 'zt' (Traditional Chinese) not found in /languages response"
  warn "The Argos Translate index may not have included zt packages at image build time."
  warn "If zt support is required for this release, the release owner must explicitly"
  warn "accept this limitation before marking the artifact as approved."
fi

# ---------------------------------------------------------------------------
# 3. Test required translation pairs (to and from English)
#
# Short deterministic phrases are used; translation quality is not validated.
# The check verifies that the service accepts the request and returns a
# translatedText field without error, confirming the language pair is installed.
# ---------------------------------------------------------------------------
do_translate() {
  local source="$1" target="$2" phrase="$3"
  local payload response
  payload=$(printf '{"q":"%s","source":"%s","target":"%s"}' "${phrase}" "${source}" "${target}")
  response=$(curl -fsS --max-time "${TIMEOUT}" \
    -X POST "${LIBRETRANSLATE_URL}/translate" \
    -H "Content-Type: application/json" \
    -d "${payload}") \
    || fail "Translation request failed for ${source}->${target} (phrase='${phrase}')"
  printf '%s' "$response" | grep -q '"translatedText"' \
    || fail "Response for ${source}->${target} does not contain 'translatedText'"
  log "Translation pair verified: ${source} -> ${target}"
}

# en -> required non-English languages
do_translate en ar "hello"
do_translate en fr "hello"
do_translate en ru "hello"
do_translate en es "hello"
do_translate en zh "hello"
do_translate en ko "hello"
do_translate en th "hello"
do_translate en he "hello"

# required non-English languages -> en
# Using ASCII "hello" as the source phrase is sufficient to confirm the pair
# is functional; the service responds without error regardless of source language.
do_translate ar en "hello"
do_translate fr en "hello"
do_translate ru en "hello"
do_translate es en "hello"
do_translate zh en "hello"
do_translate ko en "hello"
do_translate th en "hello"
do_translate he en "hello"

# zt (Traditional Chinese) — optional pair test
if [[ "${zt_available}" -eq 1 ]]; then
  do_translate en zt "hello"
  do_translate zt en "hello"
else
  warn "Skipping zt (Traditional Chinese) translation pair test — language not available"
fi

log "All required translation language pairs validated successfully"
