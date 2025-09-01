#!/bin/bash

# Включаем строгий режим для безопасности
set -euo pipefail
IFS=$'\n\t'

# Устанавливаем ограничивающие разрешения
umask 077

# ERR trap для обработки ошибок
trap 'echo "❌ Ошибка в строке $LINENO. Выход." >&2; exit 1' ERR

# Скрипт для резервного копирования PostgreSQL базы данных
# Использование: ./backup_db.sh [имя_файла_бэкапа]

# Настройки из переменных окружения
DB_NAME="${POSTGRES_DB:-form_com_offer_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
# Use POSTGRES_PASSWORD if provided (safer than prompting)
export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD:-}}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-true}"
BACKUP_VERIFY_INTEGRITY="${BACKUP_VERIFY_INTEGRITY:-true}"
DATE=$(date +%Y%m%d_%H%M%S)

# Определяем user_id для логирования (по умолчанию 'root_app' для системных операций)
USER_ID="${USER_ID:-root_app}"

# Функция логирования с user_id
log_message() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - user_id=${USER_ID} | [BACKUP] ${level}: ${message}"
}

# Если имя файла не указано, используем дату
if [ -z "$1" ]; then
    BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${DATE}.sql"
else
    BACKUP_FILE="${BACKUP_DIR}/$1"
fi

# Проверяем существование директории для бэкапов и создаем если нужно
if [ ! -d "$BACKUP_DIR" ]; then
    log_message "INFO" "📁 Создаем директорию для бэкапов: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"
    log_message "INFO" "✅ Директория создана с безопасными разрешениями"
fi

log_message "INFO" "🔄 Начинаем резервное копирование базы данных $DB_NAME..."
log_message "INFO" "📁 Файл бэкапа: $BACKUP_FILE"
log_message "INFO" "🔧 Настройки: сжатие=$BACKUP_COMPRESSION, проверка=$BACKUP_VERIFY_INTEGRITY"

# Создаем резервную копию
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose --clean --create --if-exists \
    --file="$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Устанавливаем безопасные разрешения для файла бэкапа
    chmod 600 "$BACKUP_FILE"
    log_message "INFO" "✅ Резервное копирование завершено успешно!"
    log_message "INFO" "📊 Размер файла: $(du -h "$BACKUP_FILE" | cut -f1)"
    
    # Сжимаем файл если включено
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        log_message "INFO" "🗜️ Сжимаем файл..."
        gzip "$BACKUP_FILE"
        BACKUP_FILE="${BACKUP_FILE}.gz"
        # Устанавливаем безопасные разрешения для сжатого файла
        chmod 600 "$BACKUP_FILE"
        log_message "INFO" "📊 Размер после сжатия: $(du -h "$BACKUP_FILE" | cut -f1)"
    fi
    
    # Проверяем целостность если включено
    if [ "$BACKUP_VERIFY_INTEGRITY" = "true" ]; then
        log_message "INFO" "🔍 Проверка целостности..."
        if [ "$BACKUP_COMPRESSION" = "true" ]; then
            if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
                log_message "INFO" "✅ Целостность подтверждена"
            else
                log_message "ERROR" "❌ Ошибка целостности!"
                exit 1
            fi
        else
            log_message "INFO" "✅ Целостность подтверждена"
        fi
    fi
    
    # Очищаем старые бэкапы
    log_message "INFO" "🧹 Очистка старых бэкапов (старше ${BACKUP_RETENTION_DAYS} дней)..."
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        find "$BACKUP_DIR" -type f -name "backup_${DB_NAME}_*.sql.gz" -mtime +"${BACKUP_RETENTION_DAYS}" -delete 2>/dev/null
    else
        find "$BACKUP_DIR" -type f -name "backup_${DB_NAME}_*.sql" -mtime +"${BACKUP_RETENTION_DAYS}" -delete 2>/dev/null
    fi
    
    log_message "INFO" "🎉 Операция завершена!"
else
    log_message "ERROR" "❌ Ошибка при создании резервной копии!"
    exit 1
fi
