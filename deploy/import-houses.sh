#!/usr/bin/env bash
set -euo pipefail

url="${HOUSES_DATASET_URL:?HOUSES_DATASET_URL is required}"
dataset_dir="datasets"
dataset="$dataset_dir/houses.json"
digest_file=".houses_dataset.sha256"

mkdir -p "$dataset_dir"
tmp="$(mktemp "$dataset.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

echo "Downloading $url"
curl --fail --location --silent --show-error --retry 5 --retry-delay 5 --retry-all-errors \
  --connect-timeout 20 --max-time 900 --output "$tmp" "$url"
jq -e '.version == 1 and (.houses | type == "array")' "$tmp" >/dev/null

new_digest="$(sha256sum "$tmp" | cut -d' ' -f1)"
old_digest="$(cat "$digest_file" 2>/dev/null || true)"
echo "Dataset: $(du -h "$tmp" | cut -f1), sha256 $new_digest"

if [[ "$new_digest" == "$old_digest" && "${FORCE_IMPORT:-false}" != "true" ]]; then
  echo "Dataset is unchanged since the last import, skipping"
  exit 0
fi

chmod 644 "$tmp"
mv "$tmp" "$dataset"
trap - EXIT

docker compose --profile import run --rm houses-import
echo "$new_digest" >"$digest_file"
