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
export FRONTEND_IMAGE="${FRONTEND_IMAGE:-ghcr.io/${OWNER_REPO}/frontend:${IMAGE_TAG}}"
export IMAGE_TAG

COMPOSE_FILES=(-f "${BASE}" -f "${OVERLAY}")
if [[ "${NO_MONGO:-0}" == "1" ]]; then
  COMPOSE_FILES+=(-f "${COMPOSE_DIR}/docker-compose.no-mongo.yml")
fi

echo "==> Environment : ${ENV_NAME}"
echo "==> Project     : ${PROJECT}"
echo "==> Backend     : ${BACKEND_IMAGE}"
echo "==> Frontend    : ${FRONTEND_IMAGE}"
echo "==> Env file    : ${ENV_FILE}"

cd "${ROOT_DIR}"

docker compose -p "${PROJECT}" "${COMPOSE_FILES[@]}" --env-file "${ENV_FILE}" pull
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

Default host ports:
  dev  → http://HOST:8080   (API :8001, Mongo :27018)
  tst  → http://HOST:8081   (API :8002, Mongo :27019)
  uat  → http://HOST:8082   (API :8003, Mongo :27020)
  prod → http://HOST:80     (API/Mongo not published)

EOF
