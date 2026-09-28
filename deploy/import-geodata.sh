#!/usr/bin/env bash
set -euo pipefail

base_url="${GEODATA_BASE_URL:?GEODATA_BASE_URL is required}"
dataset_dir="datasets"
digest_file=".geodata.sha256"
files=(
  house_geolocation_multisource.csv
  bryansk_districts.geojson
  microsoft_buildings_bryansk.geojsonl
  microsoft_buildings_bakhchysarai.geojsonl
  bakhchisaray.geojson
)

mkdir -p "$dataset_dir"
for file in "${files[@]}"; do
  target="$dataset_dir/$file"
  echo "Downloading ${base_url%/}/$file"
  curl --fail --location --silent --show-error --retry 5 --retry-delay 5 --retry-all-errors \
    --connect-timeout 20 --max-time 900 --output "$target.tmp" "${base_url%/}/$file"
  chmod 644 "$target.tmp"
  mv "$target.tmp" "$target"
done

new_digest="$(
  {
    cat .houses_dataset.sha256 2>/dev/null || true
    for file in "${files[@]}"; do sha256sum "$dataset_dir/$file"; done
  } | sha256sum | cut -d' ' -f1
)"
old_digest="$(cat "$digest_file" 2>/dev/null || true)"

if [[ "$new_digest" == "$old_digest" && "${FORCE_IMPORT:-false}" != "true" ]]; then
  echo "Geodata and houses are unchanged since the last import, skipping"
  exit 0
fi

docker compose --profile import run --rm geodata-import
echo "$new_digest" >"$digest_file"
