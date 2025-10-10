#!/usr/bin/env bash
set -euo pipefail

# Trivy Security Scanner - Scan All Containers (Bash)

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
      echo "Найден COMPOSE_PROJECT_NAME: ${PROJECT_NAME}"
    fi
  done < "${ENV_FILE}"
fi

declare -A IMAGES
IMAGES[Backend]="${PROJECT_NAME}-backend:latest"
IMAGES[Frontend]="${PROJECT_NAME}-frontend:latest"
IMAGES[Database]="postgres:15-alpine"

REPORTS_DIR="${SCRIPT_DIR}/reports"
CACHE_DIR="${SCRIPT_DIR}/cache"
TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
SUMMARY_FILE="${REPORTS_DIR}/summary_${TIMESTAMP}.txt"

mkdir -p "${REPORTS_DIR}" "${CACHE_DIR}"

echo "Проверка Docker..."
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Установите Docker Desktop" >&2
  exit 1
fi

echo "Загрузка образа Trivy..."
if ! docker pull aquasec/trivy:0.66.0; then
  echo "Не удалось загрузить образ Trivy" >&2
  exit 1
fi

scan_image() {
  local image_name="$1"
  local display_name="$2"

  echo >&2
  echo "Сканирование: ${display_name}" >&2

  # Use image name directly
  local image_ref="${image_name}"

  # Check if image exists locally
  if [[ -z "$(docker images -q "${image_ref}" 2>/dev/null)" ]]; then
    echo "Образ '${image_ref}' не найден локально для '${display_name}'. Пропуск." >&2
    echo "SKIPPED|${display_name}|${image_ref}|0|0|0|0"
    return 0
  fi

  local safe_image_name
  safe_image_name="${image_ref/:/_}"
  safe_image_name="${safe_image_name//\//_}"

  local json_report="${REPORTS_DIR}/scan_${safe_image_name}_${TIMESTAMP}.json"
  local table_report="${REPORTS_DIR}/scan_${safe_image_name}_${TIMESTAMP}.txt"

  echo "Генерация отчета (table)..." >&2
  export MSYS_NO_PATHCONV=1
  export MSYS2_ARG_CONV_EXCL="*"
  docker run --rm \
    -v //var/run/docker.sock:/var/run/docker.sock \
    -v "${SCRIPT_DIR}:/config:ro" \
    -v "${REPORTS_DIR}:/reports" \
    -v "${CACHE_DIR}:/cache" \
    -e TRIVY_CACHE_DIR=/cache \
    aquasec/trivy:0.66.0 \
    image \
    --severity CRITICAL,HIGH,MEDIUM \
    --format table \
    --output /reports/temp_table.txt \
    "${image_ref}"

  [[ -f "${REPORTS_DIR}/temp_table.txt" ]] && mv -f "${REPORTS_DIR}/temp_table.txt" "${table_report}"

  echo "Генерация отчета (JSON)..." >&2
  docker run --rm \
    -v //var/run/docker.sock:/var/run/docker.sock \
    -v "${SCRIPT_DIR}:/config:ro" \
    -v "${REPORTS_DIR}:/reports" \
    -v "${CACHE_DIR}:/cache" \
    -e TRIVY_CACHE_DIR=/cache \
    aquasec/trivy:0.66.0 \
    image \
    --severity CRITICAL,HIGH,MEDIUM,LOW \
    --format json \
    --output /reports/temp_json.json \
    "${image_ref}"

  [[ -f "${REPORTS_DIR}/temp_json.json" ]] && mv -f "${REPORTS_DIR}/temp_json.json" "${json_report}"

  local critical=0 high=0 medium=0 low=0
  if [[ -s "${json_report}" ]]; then
    # simple parse counts by severity
    critical=$(grep -o '"Severity"\s*:\s*"CRITICAL"' "${json_report}" | wc -l | tr -d ' ')
    high=$(grep -o '"Severity"\s*:\s*"HIGH"' "${json_report}" | wc -l | tr -d ' ')
    medium=$(grep -o '"Severity"\s*:\s*"MEDIUM"' "${json_report}" | wc -l | tr -d ' ')
    low=$(grep -o '"Severity"\s*:\s*"LOW"' "${json_report}" | wc -l | tr -d ' ')
  fi

  # Возвращаем результат в stdout, остальные сообщения в stderr
  echo "Completed|${display_name}|${image_ref}|${critical}|${high}|${medium}|${low}"
  echo "Отчеты сохранены:" >&2
  echo "- JSON:  ${json_report}" >&2
  echo "- Table: ${table_report}" >&2
}

# Initialize counters
total_critical=0 total_high=0 total_medium=0 total_low=0
completed=0 skipped=0 errors=0

results=()
for key in "${!IMAGES[@]}"; do
  line=$(scan_image "${IMAGES[$key]}" "$key")
  results+=("$line")
  sleep 1
done

{
  echo "================================================================================"
  echo "                    TRIVY SECURITY SCAN SUMMARY"
  echo "================================================================================"
  echo "Дата сканирования: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "Проект: ${PROJECT_NAME}"
  echo
  for r in "${results[@]}"; do
    IFS='|' read -r status name image c h m l <<<"$r"
    echo "--------------------------------------------------------------------------------"
    echo "${name} (${image})"
    echo "--------------------------------------------------------------------------------"
    echo "Статус: ${status}"
    echo "Уязвимости:"
    echo "  CRITICAL: ${c:-0}"
    echo "  HIGH:     ${h:-0}"
    echo "  MEDIUM:   ${m:-0}"
    echo "  LOW:      ${l:-0}"
    echo
    if [[ "$status" == "Completed" ]]; then completed=$((completed+1)); fi
    if [[ "$status" == "SKIPPED" ]]; then skipped=$((skipped+1)); fi
    if [[ "$status" == "Error" ]]; then errors=$((errors+1)); fi
    # Safely add numbers with default 0
    total_critical=$((total_critical + ${c:-0}))
    total_high=$((total_high + ${h:-0}))
    total_medium=$((total_medium + ${m:-0}))
    total_low=$((total_low + ${l:-0}))
  done

  echo "================================================================================"
  echo "ОБЩАЯ СТАТИСТИКА"
  echo "================================================================================"
  echo "Всего образов: ${#results[@]}"
  echo "Просканировано: ${completed}"
  echo "Пропущено: ${skipped}"
  echo "Ошибок: ${errors}"
  echo
  echo "Всего уязвимостей:"
  echo "  CRITICAL: ${total_critical}"
  echo "  HIGH:     ${total_high}"
  echo "  MEDIUM:   ${total_medium}"
  echo "  LOW:      ${total_low}"
  echo
  echo "================================================================================"
  echo "РЕКОМЕНДАЦИИ"
  echo "================================================================================"
  if (( total_critical > 0 )); then
    echo "ВНИМАНИЕ! Обнаружены CRITICAL уязвимости! Требуется немедленное исправление!"
  elif (( total_high > 0 )); then
    echo "Обнаружены HIGH уязвимости. Рекомендуется исправить в ближайшее время."
  else
    echo "Критических уязвимостей не обнаружено."
  fi
  echo
  echo "Детальные отчёты сохранены в: ${REPORTS_DIR}"
} | tee "${SUMMARY_FILE}"

echo "Итоговый отчёт сохранён: ${SUMMARY_FILE}"

# Exit code policy
if (( total_critical > 0 )); then
  exit 1
fi
exit 0


