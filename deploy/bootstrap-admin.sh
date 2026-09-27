#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${STAFF_ADMIN_LOGIN:-}" || -z "${STAFF_ADMIN_PASSWORD:-}" ]]; then
  echo "::warning::STAFF_ADMIN_LOGIN or STAFF_ADMIN_PASSWORD is not set, skipping admin bootstrap"
  exit 0
fi

export STAFF_ADMIN_DISPLAY_NAME="${STAFF_ADMIN_DISPLAY_NAME:-Главный администратор}"
export STAFF_ADMIN_EMAIL="${STAFF_ADMIN_EMAIL:-}"

docker compose exec -T \
  -e STAFF_ADMIN_LOGIN \
  -e STAFF_ADMIN_PASSWORD \
  -e STAFF_ADMIN_DISPLAY_NAME \
  -e STAFF_ADMIN_EMAIL \
  backend python - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request

secret = os.environ.get("STAFF_BOOTSTRAP_SECRET")
if not secret:
    sys.exit("STAFF_BOOTSTRAP_SECRET is not set in the backend container")

login = os.environ["STAFF_ADMIN_LOGIN"]
payload = {
    "login": login,
    "password": os.environ["STAFF_ADMIN_PASSWORD"],
    "display_name": os.environ["STAFF_ADMIN_DISPLAY_NAME"],
    "role": "admin",
    "email": os.environ["STAFF_ADMIN_EMAIL"] or None,
}
request = urllib.request.Request(
    "http://127.0.0.1:8000/auth/staff/register",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "X-Bootstrap-Secret": secret},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print(f"Admin {login!r} created (HTTP {response.status})")
except urllib.error.HTTPError as exc:
    if exc.code == 409:
        print(f"Admin {login!r} already exists, nothing to do")
    else:
        sys.exit(f"Admin bootstrap failed: HTTP {exc.code} {exc.read().decode(errors='replace')[:500]}")
PY
