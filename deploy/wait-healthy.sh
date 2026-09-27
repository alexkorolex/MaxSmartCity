#!/usr/bin/env bash
set -euo pipefail

timeout="${WAIT_TIMEOUT:-900}"
deadline=$((SECONDS + timeout))

while :; do
  pending=()
  failed=()

  while IFS='|' read -r name state health exit_code; do
    [[ -z "$name" ]] && continue
    case "$state" in
      running)
        case "$health" in
          "" | healthy) ;;
          unhealthy) failed+=("$name (unhealthy)") ;;
          *) pending+=("$name ($health)") ;;
        esac
        ;;
      exited)
        [[ "$exit_code" == "0" ]] || failed+=("$name (exit $exit_code)")
        ;;
      dead) failed+=("$name (dead)") ;;
      *) pending+=("$name ($state)") ;;
    esac
  done < <(docker compose ps --all --format '{{.Name}}|{{.State}}|{{.Health}}|{{.ExitCode}}')

  if ((${#failed[@]})); then
    printf 'Failed: %s\n' "${failed[@]}" >&2
    exit 1
  fi

  if ((${#pending[@]} == 0)); then
    echo "All services are healthy"
    exit 0
  fi

  if ((SECONDS >= deadline)); then
    printf 'Timed out after %ss waiting for: %s\n' "$timeout" "${pending[*]}" >&2
    exit 1
  fi

  echo "Waiting for: ${pending[*]}"
  sleep 5
done
