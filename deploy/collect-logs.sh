#!/usr/bin/env bash
set -uo pipefail

logs_dir="${1:?usage: collect-logs.sh <logs-dir>}"
mkdir -p "$logs_dir/services"

if [[ -f .env ]]; then
  docker compose ps --all >"$logs_dir/compose-ps.txt" 2>&1
  docker compose logs --no-color --timestamps --tail="${LOG_TAIL_LINES:-3000}" >"$logs_dir/compose.log" 2>&1
  while read -r service; do
    [[ -n "$service" ]] || continue
    docker compose logs --no-color --timestamps --tail="${LOG_TAIL_LINES:-3000}" "$service" \
      >"$logs_dir/services/$service.log" 2>&1
  done < <(docker compose ps --all --services 2>/dev/null)
fi

docker system df >"$logs_dir/docker-df.txt" 2>&1
df -h >"$logs_dir/disk.txt" 2>&1

mapfile -t sensitive < <(jq -r '.[]? | tostring | select(length >= 4)' <<<"${SECRETS_JSON:-"{}"}" 2>/dev/null)

if ((${#sensitive[@]})); then
  while IFS= read -r -d '' file; do
    content="$(<"$file")"
    for value in "${sensitive[@]}"; do
      content="${content//"$value"/***}"
    done
    printf '%s\n' "$content" >"$file"
  done < <(find "$logs_dir" -type f -print0)
fi

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "## Deploy failure logs"
    for file in "$logs_dir"/*.log "$logs_dir"/compose-ps.txt; do
      [[ -s "$file" ]] || continue
      echo "<details><summary>$(basename "$file")</summary>"
      echo
      echo '```'
      tail -n 80 "$file"
      echo '```'
      echo "</details>"
    done
  } >>"$GITHUB_STEP_SUMMARY"
fi

exit 0
