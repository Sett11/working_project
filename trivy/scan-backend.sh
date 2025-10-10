#!/usr/bin/env bash
set -euo pipefail

# Trivy Security Scanner - Scan Backend Only (Bash)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV_FILE="${PROJECT_ROOT}/.env"
PROJECT_NAME="working_project"

if [[ -f "${ENV_FILE}" ]]; then
  # read .env safely
  while IFS= read -r line; do
    if [[ "$line" =~ ^COMPOSE_PROJECT_NAME=(.+)$ ]]; then
      PROJECT_NAME="${BASH_REMATCH[1]}"
      # strip potential CR
      PROJECT_NAME="${PROJECT_NAME%$'\r'}"
    fi
  done < "${ENV_FILE}"
fi

CONTAINER_NAME="${PROJECT_NAME}-backend"
TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
REPORTS_DIR="${SCRIPT_DIR}/reports"
CACHE_DIR="${SCRIPT_DIR}/cache"

echo
echo "TRIVY - Сканирование Backend образа"
echo "Контейнер: ${CONTAINER_NAME}"

# Check docker
if ! command -v docker >/dev/null 2>&1; then
  echo "Ошибка: docker не найден в PATH" >&2
  exit 1
fi

# Resolve image reference
IMAGE_REF=""
if docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
  IMAGE_REF="$(docker inspect -f '{{.Image}}' "${CONTAINER_NAME}" 2>/dev/null || echo '')"
  if [[ -z "${IMAGE_REF}" ]]; then
    # Fallback to image name if Image field is empty
    IMAGE_REF="${CONTAINER_NAME}"
  fi
fi

# Fallbacks by common compose tags if container not found
if [[ -z "${IMAGE_REF}" ]]; then
  CANDIDATES=(
    "${PROJECT_NAME}-backend:latest"
    "${PROJECT_NAME}-backend"
  )
  for cand in "${CANDIDATES[@]}"; do
    if docker image inspect "${cand}" >/dev/null 2>&1; then
      IMAGE_REF="${cand}"
      break
    fi
  done
fi

if [[ -z "${IMAGE_REF}" ]]; then
  echo "Не удалось определить образ для контейнера '${CONTAINER_NAME}'. Выполните: docker compose build backend && docker compose up -d backend" >&2
  exit 1
fi

# Не выполняем дополнительную проверку наличия образа, Trivy сам сообщит об ошибке

mkdir -p "${REPORTS_DIR}" "${CACHE_DIR}"

JSON_REPORT="${REPORTS_DIR}/scan_backend_${TIMESTAMP}.json"
TABLE_REPORT="${REPORTS_DIR}/scan_backend_${TIMESTAMP}.txt"

echo "Запуск сканирования (table format)..."
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"
docker run --rm \
  -v //var/run/docker.sock:/var/run/docker.sock \
  -v "${REPORTS_DIR}:/reports" \
  -v "${CACHE_DIR}:/cache" \
  -e TRIVY_CACHE_DIR=/cache \
  aquasec/trivy:0.66.0 \
  image \
  --severity CRITICAL,HIGH,MEDIUM \
  --format table \
  --output /reports/temp_backend.txt \
  "${IMAGE_REF}"

TEMP_TABLE_FILE="${REPORTS_DIR}/temp_backend.txt"
if [[ ! -s "${TEMP_TABLE_FILE}" ]]; then
  echo "Ошибка: файл отчета temp_backend.txt отсутствует или пуст" >&2
  [[ -f "${TEMP_TABLE_FILE}" ]] && rm -f "${TEMP_TABLE_FILE}"
  exit 1
fi
mv -f "${TEMP_TABLE_FILE}" "${TABLE_REPORT}"
echo "Table отчёт сохранён: ${TABLE_REPORT}"

echo "Запуск сканирования (JSON format)..."
docker run --rm \
  -v //var/run/docker.sock:/var/run/docker.sock \
  -v "${REPORTS_DIR}:/reports" \
  -v "${CACHE_DIR}:/cache" \
  -e TRIVY_CACHE_DIR=/cache \
  aquasec/trivy:0.66.0 \
  image \
  --severity CRITICAL,HIGH,MEDIUM,LOW \
  --format json \
  --output /reports/temp_backend.json \
  "${IMAGE_REF}"

TEMP_JSON_FILE="${REPORTS_DIR}/temp_backend.json"
if [[ ! -s "${TEMP_JSON_FILE}" ]]; then
  echo "Ошибка: файл отчета temp_backend.json отсутствует или пуст" >&2
  [[ -f "${TEMP_JSON_FILE}" ]] && rm -f "${TEMP_JSON_FILE}"
  exit 1
fi
mv -f "${TEMP_JSON_FILE}" "${JSON_REPORT}"
echo "JSON отчёт сохранён: ${JSON_REPORT}"

echo
echo "Сканирование завершено"
echo "Отчёты: ${REPORTS_DIR}"
echo "- JSON:  ${JSON_REPORT}"
echo "- Table: ${TABLE_REPORT}"


