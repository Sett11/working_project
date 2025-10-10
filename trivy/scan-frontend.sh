#!/usr/bin/env bash
set -euo pipefail

# Trivy Security Scanner - Scan Frontend Only (Bash)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV_FILE="${PROJECT_ROOT}/.env"
PROJECT_NAME="working_project"

if [[ -f "${ENV_FILE}" ]]; then
  while IFS= read -r line; do
    if [[ "$line" =~ ^COMPOSE_PROJECT_NAME=(.+)$ ]]; then
      PROJECT_NAME="${BASH_REMATCH[1]}"
      # Убираем символы возврата каретки
      PROJECT_NAME="${PROJECT_NAME%$'\r'}"
    fi
  done < "${ENV_FILE}"
fi

CONTAINER_NAME="${PROJECT_NAME}-frontend"
TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
REPORTS_DIR="${SCRIPT_DIR}/reports"
CACHE_DIR="${SCRIPT_DIR}/cache"

echo
echo "TRIVY - Сканирование Frontend образа"
echo "Контейнер: ${CONTAINER_NAME}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Ошибка: docker не найден в PATH" >&2
  exit 1
fi

# Resolve image from container name
if docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
  IMAGE_REF="$(docker inspect -f '{{.Image}}' "${CONTAINER_NAME}" 2>/dev/null || echo '')"
  if [[ -z "${IMAGE_REF}" ]]; then
    # Fallback to image name if Image field is empty
    IMAGE_REF="${CONTAINER_NAME}"
  fi
else
  IMAGE_REF="${CONTAINER_NAME}"
fi

if [[ -z "$(docker images -q "${IMAGE_REF}" 2>/dev/null)" ]]; then
  echo "Образ для контейнера '${CONTAINER_NAME}' не найден локально (ref: ${IMAGE_REF}). Соберите его: docker compose build frontend" >&2
  exit 1
fi

mkdir -p "${REPORTS_DIR}" "${CACHE_DIR}"

JSON_REPORT="${REPORTS_DIR}/scan_frontend_${TIMESTAMP}.json"
TABLE_REPORT="${REPORTS_DIR}/scan_frontend_${TIMESTAMP}.txt"

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
  --output /reports/temp_frontend.txt \
  "${IMAGE_REF}"

TEMP_TABLE_FILE="${REPORTS_DIR}/temp_frontend.txt"
if [[ ! -s "${TEMP_TABLE_FILE}" ]]; then
  echo "Ошибка: файл отчета temp_frontend.txt отсутствует или пуст" >&2
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
  --output /reports/temp_frontend.json \
  "${IMAGE_REF}"

TEMP_JSON_FILE="${REPORTS_DIR}/temp_frontend.json"
if [[ ! -s "${TEMP_JSON_FILE}" ]]; then
  echo "Ошибка: файл отчета temp_frontend.json отсутствует или пуст" >&2
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


