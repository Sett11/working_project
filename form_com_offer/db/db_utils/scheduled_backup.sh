#!/bin/bash

# Скрипт для автоматического резервного копирования по расписанию
# Рекомендуется добавить в crontab: 0 2 * * * /path/to/scheduled_backup.sh

# Настройки из переменных окружения
DB_NAME="${POSTGRES_DB:-form_com_offer_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="/backups"
LOG_FILE="/backups/backup.log"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-true}"
BACKUP_VERIFY_INTEGRITY="${BACKUP_VERIFY_INTEGRITY:-true}"
MAX_BACKUPS="${MAX_BACKUPS:-10}"
DATE=$(date +%Y%m%d_%H%M%S)

# Функция логирования
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Проверяем существование директории для бэкапов
if [ ! -d "$BACKUP_DIR" ]; then
    log_message "❌ Директория для бэкапов не найдена: $BACKUP_DIR"
    exit 1
fi

log_message "🔄 Начинаем автоматическое резервное копирование..."
log_message "🔧 Настройки: сжатие=$BACKUP_COMPRESSION, проверка=$BACKUP_VERIFY_INTEGRITY, хранение=$BACKUP_RETENTION_DAYS дней"

# Проверяем подключение к БД
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" >/dev/null 2>&1; then
    log_message "❌ База данных недоступна"
    exit 1
fi

# Создаем резервную копию
BACKUP_FILE="${BACKUP_DIR}/auto_backup_${DB_NAME}_${DATE}.sql"
log_message "📁 Создаем резервную копию: $BACKUP_FILE"

# Создаем резервную копию с сжатием
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose --clean --create --if-exists \
    --file="$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    # Сжимаем файл для экономии места если включено
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        log_message "🗜️ Сжимаем файл..."
        gzip "$BACKUP_FILE"
        BACKUP_FILE="${BACKUP_FILE}.gz"
    fi
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_message "✅ Резервное копирование завершено успешно! Размер: $BACKUP_SIZE"
    
    # Проверяем целостность если включено
    if [ "$BACKUP_VERIFY_INTEGRITY" = "true" ]; then
        log_message "🔍 Проверка целостности резервной копии..."
        if [ "$BACKUP_COMPRESSION" = "true" ]; then
            if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
                log_message "✅ Целостность резервной копии подтверждена"
            else
                log_message "❌ Ошибка целостности резервной копии!"
                exit 1
            fi
        else
            log_message "✅ Целостность резервной копии подтверждена"
        fi
    fi
    
    # Очищаем старые бэкапы
    log_message "🧹 Очистка старых резервных копий..."
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        find "$BACKUP_DIR" -name "auto_backup_${DB_NAME}_*.sql.gz" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null
    else
        find "$BACKUP_DIR" -name "auto_backup_${DB_NAME}_*.sql" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null
    fi
    
    # Проверяем количество оставшихся бэкапов
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        REMAINING_BACKUPS=$(ls -1 "${BACKUP_DIR}/auto_backup_${DB_NAME}_"*.sql.gz 2>/dev/null | wc -l)
    else
        REMAINING_BACKUPS=$(ls -1 "${BACKUP_DIR}/auto_backup_${DB_NAME}_"*.sql 2>/dev/null | wc -l)
    fi
    log_message "📊 Осталось резервных копий: $REMAINING_BACKUPS"
    
    log_message "🎉 Автоматическое резервное копирование завершено успешно!"
else
    log_message "❌ Ошибка при создании резервной копии!"
    exit 1
fi

# Очистка старых логов (оставляем последние 1000 строк)
if [ -f "$LOG_FILE" ]; then
    tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi
