#!/usr/bin/env bash
# Deploy (or refresh) one environment from GHCR images.
#
# Usage:
#   ./deploy/scripts/deploy-env.sh <dev|tst|uat|prod> [image_tag]
#
# Examples:
#   ./deploy/scripts/deploy-env.sh uat
#   ./deploy/scripts/deploy-env.sh prod v1.2.3
#   IMAGE_TAG=sha-abc1234 ./deploy/scripts/deploy-env.sh tst
#   NO_MONGO=1 ./deploy/scripts/deploy-env.sh uat
#   BIND_MOUNTS=1 ./deploy/scripts/deploy-env.sh uat
#   BIND_MOUNTS=1 HOST_DATA_ROOT=/var/lib/telegram-copier ./deploy/scripts/deploy-env.sh prod
#   SKIP_PULL=1 BACKEND_IMAGE=local/tgc-backend:dev ./deploy/scripts/deploy-env.sh dev
#
# Data (default = Docker named volumes, isolated per Compose project tgc-<env>):
#   tgc-<env>_app_data   → container /app/data  (SQLite, sessions, media)
#   tgc-<env>_mongo_data → container /data/db   (MongoDB files)
# With BIND_MOUNTS=1, same paths are bind-mounted from the host instead.
#
# Prerequisites:
#   - Docker Engine + Compose plugin
#   - Logged in to GHCR if the package is private:
#       echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
#   - Real env file at deploy/env/docker.env.<env> (copy from *.example)

set -euo pipefail

ENV_NAME="${1:-}"
IMAGE_TAG="${2:-${IMAGE_TAG:-latest}}"

if [[ -z "${ENV_NAME}" ]]; then
  echo "Usage: $0 <dev|tst|uat|prod> [image_tag]" >&2
  exit 1
fi

case "${ENV_NAME}" in
  dev|tst|uat|prod) ;;
  *)
    echo "Unknown environment: ${ENV_NAME} (expected: dev|tst|uat|prod)" >&2
    exit 1
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_DIR="${ROOT_DIR}/deploy/compose"
ENV_FILE="${ROOT_DIR}/deploy/env/docker.env.${ENV_NAME}"
OVERLAY="${COMPOSE_DIR}/docker-compose.${ENV_NAME}.yml"
BASE="${COMPOSE_DIR}/docker-compose.yml"
PROJECT="tgc-${ENV_NAME}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  echo "Copy deploy/env/docker.env.${ENV_NAME}.example → deploy/env/docker.env.${ENV_NAME} and fill secrets." >&2
  exit 1
fi

if [[ ! -f "${OVERLAY}" ]]; then
  echo "Missing compose overlay: ${OVERLAY}" >&2
  exit 1
fi

OWNER_REPO_DEFAULT="sammirzagharcheh/pytelegramclientcopier"
OWNER_REPO="${GHCR_OWNER_REPO:-${OWNER_REPO_DEFAULT}}"
export BACKEND_IMAGE="${BACKEND_IMAGE:-ghcr.io/${OWNER_REPO}/backend:${IMAGE_TAG}}"
export IMAGE_TAG
export COMPOSE_ENV="${ENV_NAME}"
export HOST_DATA_ROOT="${HOST_DATA_ROOT:-${ROOT_DIR}/data/docker-envs}"
if [[ "${SKIP_PULL:-0}" == "1" ]]; then
  export PULL_POLICY="${PULL_POLICY:-missing}"
else
  export PULL_POLICY="${PULL_POLICY:-always}"
fi

COMPOSE_FILES=(-f "${BASE}" -f "${OVERLAY}")
if [[ "${NO_MONGO:-0}" == "1" ]]; then
  COMPOSE_FILES+=(-f "${COMPOSE_DIR}/docker-compose.no-mongo.yml")
fi
if [[ "${BIND_MOUNTS:-0}" == "1" ]]; then
  mkdir -p "${HOST_DATA_ROOT}/${ENV_NAME}/app" "${HOST_DATA_ROOT}/${ENV_NAME}/mongo"
  COMPOSE_FILES+=(-f "${COMPOSE_DIR}/docker-compose.bind-mounts.yml")
fi

echo "==> Environment : ${ENV_NAME}"
echo "==> Project     : ${PROJECT}"
echo "==> Image       : ${BACKEND_IMAGE}"
echo "==> Env file    : ${ENV_FILE}"
if [[ "${BIND_MOUNTS:-0}" == "1" ]]; then
  echo "==> Data mode   : host bind mounts under ${HOST_DATA_ROOT}/${ENV_NAME}/"
  echo "                 app → …/app  (SQLite, sessions, media)"
  echo "                 mongo → …/mongo"
else
  echo "==> Data mode   : Docker named volumes"
  echo "                 ${PROJECT}_app_data   → /app/data"
  echo "                 ${PROJECT}_mongo_data → /data/db"
fi

cd "${ROOT_DIR}"

if [[ "${SKIP_PULL:-0}" == "1" ]]; then
  echo "==> Skipping image pull (SKIP_PULL=1)"
else
  docker compose -p "${PROJECT}" "${COMPOSE_FILES[@]}" --env-file "${ENV_FILE}" pull
fi
docker compose -p "${PROJECT}" "${COMPOSE_FILES[@]}" --env-file "${ENV_FILE}" up -d --remove-orphans

echo
echo "==> Status"
docker compose -p "${PROJECT}" "${COMPOSE_FILES[@]}" --env-file "${ENV_FILE}" ps

cat <<EOF

Done. Next steps (first deploy only):
  docker compose -p ${PROJECT} \\
    -f deploy/compose/docker-compose.yml \\
    -f deploy/compose/docker-compose.${ENV_NAME}.yml \\
    --env-file ${ENV_FILE} \\
    exec backend tg-copier db create-admin you@example.com 'YourStrongPassword'

Default host ports (panel = SPA + /api on same port):
  dev  → http://HOST:8080   (API alias :8001, Mongo :27018)
  tst  → http://HOST:8081   (API alias :8002, Mongo :27019)
  uat  → http://HOST:8082   (API alias :8003, Mongo :27020)
  prod → http://HOST:80     (Mongo not published)

Data (this env):
  named volumes: docker volume ls | grep ${PROJECT}
  or bind mounts: ${HOST_DATA_ROOT}/${ENV_NAME}/   (when BIND_MOUNTS=1)

EOF
