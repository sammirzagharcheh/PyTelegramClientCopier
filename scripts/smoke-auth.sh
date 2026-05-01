#!/usr/bin/env bash
# Post-deploy auth smoke test.
# Usage:
#   bash scripts/smoke-auth.sh "user@example.com" "password"
#   API_BASE="http://127.0.0.1:8000/api" bash scripts/smoke-auth.sh "user@example.com" "password"

set -euo pipefail

EMAIL="${1:-}"
PASSWORD="${2:-}"
API_BASE="${API_BASE:-http://127.0.0.1:8000/api}"
HEALTH_URL="${API_BASE%/api}/health"

if [[ -z "$EMAIL" || -z "$PASSWORD" ]]; then
  echo "Usage: bash scripts/smoke-auth.sh <email> <password>"
  exit 1
fi

tmp_login="$(mktemp)"
tmp_me="$(mktemp)"
trap 'rm -f "$tmp_login" "$tmp_me"' EXIT

echo "==> Health check: $HEALTH_URL"
health_code="$(curl -sS -o /dev/null -w "%{http_code}" "$HEALTH_URL" || true)"
if [[ "$health_code" != "200" ]]; then
  echo "Health check failed (HTTP $health_code)"
  exit 1
fi
echo "Health OK"

echo "==> Login check: $API_BASE/auth/login"
login_code="$(curl -sS -o "$tmp_login" -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  "$API_BASE/auth/login" || true)"

if [[ "$login_code" != "200" ]]; then
  echo "Login failed (HTTP $login_code)"
  sed -n '1,200p' "$tmp_login"
  exit 1
fi

access_token="$(
python3 - "$tmp_login" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)
print(data.get("access_token", ""))
PY
)"

if [[ -z "$access_token" ]]; then
  echo "Login response missing access_token"
  sed -n '1,200p' "$tmp_login"
  exit 1
fi
echo "Login OK"

echo "==> Auth check: $API_BASE/auth/me"
me_code="$(curl -sS -o "$tmp_me" -w "%{http_code}" \
  -H "Authorization: Bearer $access_token" \
  "$API_BASE/auth/me" || true)"

if [[ "$me_code" != "200" ]]; then
  echo "auth/me failed (HTTP $me_code)"
  sed -n '1,200p' "$tmp_me"
  exit 1
fi

echo "auth/me OK"
echo "Smoke auth test passed."
