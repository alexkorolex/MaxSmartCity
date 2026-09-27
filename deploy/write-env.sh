#!/usr/bin/env bash
set -euo pipefail

target="${1:?usage: write-env.sh <path-to-.env>}"
empty_json='{}'
umask 077
tmp="$(mktemp "${target}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

jq -rn \
  --argjson vars "${VARS_JSON:-$empty_json}" \
  --argjson secrets "${SECRETS_JSON:-$empty_json}" \
  --arg image_tag "${IMAGE_TAG:?IMAGE_TAG is required}" \
  --arg image_prefix "${IMAGE_PREFIX:-maxsmartcity}" \
  --arg q "'" \
  '
  ($vars + $secrets + {IMAGE_TAG: $image_tag, IMAGE_PREFIX: $image_prefix})
  | del(.github_token, .GITHUB_TOKEN)
  | to_entries
  | sort_by(.key)
  | .[]
  | if (.key | test("^[A-Za-z_][A-Za-z0-9_]*$") | not) then
      error("invalid variable name: \(.key)")
    elif (.value | tostring | test("[\($q)\n\r]")) then
      error("\(.key): single quotes and line breaks are not supported in values")
    else
      "\(.key)=\($q)\(.value | tostring)\($q)"
    end
  ' >"$tmp"

mv "$tmp" "$target"
trap - EXIT
echo "Wrote $(wc -l <"$target" | tr -d ' ') variables to $target"
