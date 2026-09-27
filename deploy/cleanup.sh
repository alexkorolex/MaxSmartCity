#!/usr/bin/env bash
set -euo pipefail

prefix="${IMAGE_PREFIX:-maxsmartcity}"
keep=" ${IMAGE_TAG:?IMAGE_TAG is required} ${PREVIOUS_TAG:-} "

while read -r ref; do
  tag="${ref##*:}"
  [[ "$tag" == RELEASE.* || "$keep" == *" $tag "* ]] || docker image rm "$ref" || true
done < <(docker image ls --format '{{.Repository}}:{{.Tag}}' --filter "reference=${prefix}/*")

docker image prune --force
docker builder prune --force --filter "until=${BUILD_CACHE_TTL:-336h}"
