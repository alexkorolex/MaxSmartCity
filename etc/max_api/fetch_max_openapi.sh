#!/usr/bin/env bash
set -euo pipefail

URL="https://raw.githubusercontent.com/max-messenger/api-schema/refs/heads/main/schema.yaml"
OUT="${1:-max_api_schema.yaml}"

curl --fail --location --silent --show-error "$URL" -o "$OUT"

echo "Saved: $OUT"
grep -m1 -A2 '^info:' "$OUT" || true
