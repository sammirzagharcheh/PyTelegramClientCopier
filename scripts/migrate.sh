#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-dev}"
ACTION="${2:-upgrade}"
REVISION="${3:-head}"

case "$ENVIRONMENT" in
  dev) DB_NAME="telegram_copier_dev" ;;
  test) DB_NAME="telegram_copier_test" ;;
  prod) DB_NAME="telegram_copier_prod" ;;
  *)
    echo "Unsupported environment: $ENVIRONMENT (use dev|test|prod)" >&2
    exit 1
    ;;
esac

if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "PGPASSWORD is required. Export it before running." >&2
  exit 1
fi

PGUSER="${PGUSER:-8n8user}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"

python3 - <<'PY' >/tmp/tgc_pg_pwd_encoded.txt
import os
from urllib.parse import quote
print(quote(os.environ["PGPASSWORD"], safe=""))
PY
ENCODED_PG_PASSWORD="$(cat /tmp/tgc_pg_pwd_encoded.txt)"
rm -f /tmp/tgc_pg_pwd_encoded.txt

export DB_BACKEND="postgres"
export DATABASE_URL="postgresql+asyncpg://${PGUSER}:${ENCODED_PG_PASSWORD}@${PGHOST}:${PGPORT}/${DB_NAME}"

echo "Environment: ${ENVIRONMENT} (${DB_NAME})"
echo "Action: ${ACTION} ${REVISION}"

if [[ -x "./.venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="./.venv/Scripts/python.exe"
elif [[ -x "./.venv/Scripts/python" ]]; then
  PYTHON_BIN="./.venv/Scripts/python"
elif [[ -x "./.venv/bin/python" ]]; then
  PYTHON_BIN="./.venv/bin/python"
else
  echo "Could not find project virtualenv python executable." >&2
  exit 1
fi

case "$ACTION" in
  upgrade)
    "$PYTHON_BIN" -m alembic upgrade "$REVISION"
    ;;
  downgrade)
    "$PYTHON_BIN" -m alembic downgrade "$REVISION"
    ;;
  current)
    "$PYTHON_BIN" -m alembic current
    ;;
  history)
    "$PYTHON_BIN" -m alembic history --verbose
    ;;
  *)
    echo "Unsupported action: $ACTION (use upgrade|downgrade|current|history)" >&2
    exit 1
    ;;
esac
