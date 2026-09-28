#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T \
  -e REALM="${KEYCLOAK_REALM:-maxsmartcity}" \
  -e CLIENT_ID="${KEYCLOAK_CLIENT_ID:-maxsmartcity-backend}" \
  -e TEST_USERS="${KEYCLOAK_TEST_USERS:-admin_test housing_test uprava_test}" \
  keycloak bash -s <<'SH'
set -euo pipefail
config=/tmp/kcadm-hardening.config
trap 'rm -f "$config"' EXIT
kcadm() { /opt/keycloak/bin/kcadm.sh "$@" --config "$config"; }

kcadm config credentials --server http://localhost:8080 --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null

kcadm update "realms/$REALM" -s sslRequired=external
client_uuid="$(kcadm get clients -r "$REALM" -q clientId="$CLIENT_ID" --fields id --format csv --noquotes)"
kcadm update "clients/$client_uuid" -r "$REALM" -s standardFlowEnabled=false -s 'redirectUris=[]' -s 'webOrigins=[]'

for user in $TEST_USERS; do
  user_id="$(kcadm get users -r "$REALM" -q username="$user" -q exact=true --fields id --format csv --noquotes)"
  if [ -n "$user_id" ]; then
    kcadm delete "users/$user_id" -r "$REALM"
    echo "Removed test user $user"
  fi
done
SH
