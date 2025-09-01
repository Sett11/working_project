#!/bin/bash

# Строгий режим: выход при ошибках, неопределенных переменных и ошибках в pipeline
set -euo pipefail
# Ограничиваем права доступа к создаваемым файлам
umask 077

# Экспорт переменных окружения PostgreSQL для неинтерактивного режима
export PGHOST="${DB_HOST:-localhost}"
export PGPORT="${POSTGRES_PORT:-5432}"
export PGUSER="${POSTGRES_USER:-postgres}"
export PGDATABASE="${POSTGRES_DB:-form_com_offer_db}"
# Устанавливаем пароль из переменной окружения или используем .pgpass
if [ -n "${POSTGRES_PASSWORD:-}" ]; then
    export PGPASSWORD="$POSTGRES_PASSWORD"
elif [ -f "${HOME:-/root}/.pgpass" ]; then
    export PGPASSFILE="${HOME:-/root}/.pgpass"
fi

# Скрипт для автоматического резервного копирования по расписанию
# Рекомендуется добавить в crontab: 0 2 * * * /path/to/scheduled_backup.sh

# Настройки из переменных окружения
DB_NAME="${POSTGRES_DB:-form_com_offer_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
LOG_FILE="${LOG_FILE:-${BACKUP_DIR}/backup.log}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-true}"
BACKUP_VERIFY_INTEGRITY="${BACKUP_VERIFY_INTEGRITY:-true}"
MAX_BACKUPS="${MAX_BACKUPS:-10}"
DATE=$(date +%Y%m%d_%H%M%S)

# Определяем user_id для логирования (по умолчанию 'root_app' для системных операций)
USER_ID="${USER_ID:-root_app}"

# Функция логирования с user_id
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "${timestamp} - user_id=${USER_ID} | [SCHEDULED_BACKUP] ${level}: ${message}" | tee -a "$LOG_FILE"
}

# Проверяем существование директории для бэкапов
if [ ! -d "$BACKUP_DIR" ]; then
    log_message "ERROR" "❌ Директория для бэкапов не найдена: $BACKUP_DIR"
    exit 1
fi

log_message "INFO" "🔄 Начинаем автоматическое резервное копирование..."
log_message "INFO" "🔧 Настройки: сжатие=$BACKUP_COMPRESSION, проверка=$BACKUP_VERIFY_INTEGRITY, хранение=$BACKUP_RETENTION_DAYS дней"

# Проверяем подключение к БД
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" --no-password >/dev/null 2>&1; then
    log_message "ERROR" "❌ База данных недоступна"
    exit 1
fi

# Создаем резервную копию
BACKUP_FILE="${BACKUP_DIR}/auto_backup_${DB_NAME}_${DATE}.sql"
log_message "INFO" "📁 Создаем резервную копию: $BACKUP_FILE"

# Создаем резервную копию с сжатием
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose --clean --create --if-exists --no-password \
    --file="$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    # Сжимаем файл для экономии места если включено
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        log_message "INFO" "🗜️ Сжимаем файл..."
        gzip "$BACKUP_FILE"
        BACKUP_FILE="${BACKUP_FILE}.gz"
    fi
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_message "INFO" "✅ Резервное копирование завершено успешно! Размер: $BACKUP_SIZE"
    
    # Проверяем целостность если включено
    if [ "$BACKUP_VERIFY_INTEGRITY" = "true" ]; then
        log_message "INFO" "🔍 Проверка целостности резервной копии..."
        if [ "$BACKUP_COMPRESSION" = "true" ]; then
            if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
                log_message "INFO" "✅ Целостность резервной копии подтверждена"
            else
                log_message "ERROR" "❌ Ошибка целостности резервной копии!"
                exit 1
            fi
        else
            log_message "INFO" "✅ Целостность резервной копии подтверждена"
        fi
    fi
    
    # Очищаем старые бэкапы
    log_message "INFO" "🧹 Очистка старых резервных копий..."
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        find "$BACKUP_DIR" -maxdepth 1 -type f -name "auto_backup_${DB_NAME}_*.sql.gz" -mtime +"$BACKUP_RETENTION_DAYS" -delete 2>/dev/null
    else
        find "$BACKUP_DIR" -maxdepth 1 -type f -name "auto_backup_${DB_NAME}_*.sql" -mtime +"$BACKUP_RETENTION_DAYS" -delete 2>/dev/null
    fi
    
    # Проверяем количество оставшихся бэкапов
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        REMAINING_BACKUPS=$(ls -1 "${BACKUP_DIR}/auto_backup_${DB_NAME}_"*.sql.gz 2>/dev/null | wc -l)
    else
        REMAINING_BACKUPS=$(ls -1 "${BACKUP_DIR}/auto_backup_${DB_NAME}_"*.sql 2>/dev/null | wc -l)
    fi
    log_message "INFO" "📊 Осталось резервных копий: $REMAINING_BACKUPS"
    
    log_message "INFO" "🎉 Автоматическое резервное копирование завершено успешно!"
else
    log_message "ERROR" "❌ Ошибка при создании резервной копии!"
    exit 1
fi

# Очистка старых логов (оставляем последние 1000 строк)
if [ -f "$LOG_FILE" ]; then
    tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi
