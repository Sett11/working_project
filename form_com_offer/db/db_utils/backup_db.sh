#!/bin/bash

# Скрипт для резервного копирования PostgreSQL базы данных
# Использование: ./backup_db.sh [имя_файла_бэкапа]

# Настройки из переменных окружения
DB_NAME="${POSTGRES_DB:-form_com_offer_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="/backups"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-true}"
BACKUP_VERIFY_INTEGRITY="${BACKUP_VERIFY_INTEGRITY:-true}"
DATE=$(date +%Y%m%d_%H%M%S)

# Если имя файла не указано, используем дату
if [ -z "$1" ]; then
    BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${DATE}.sql"
else
    BACKUP_FILE="${BACKUP_DIR}/$1"
fi

# Проверяем существование директории для бэкапов
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Директория для бэкапов не найдена: $BACKUP_DIR"
    exit 1
fi

echo "🔄 Начинаем резервное копирование базы данных $DB_NAME..."
echo "📁 Файл бэкапа: $BACKUP_FILE"
echo "🔧 Настройки: сжатие=$BACKUP_COMPRESSION, проверка=$BACKUP_VERIFY_INTEGRITY"

# Создаем резервную копию
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose --clean --create --if-exists \
    --file="$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Резервное копирование завершено успешно!"
    echo "📊 Размер файла: $(du -h "$BACKUP_FILE" | cut -f1)"
    
    # Сжимаем файл если включено
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        echo "🗜️ Сжимаем файл..."
        gzip "$BACKUP_FILE"
        BACKUP_FILE="${BACKUP_FILE}.gz"
        echo "📊 Размер после сжатия: $(du -h "$BACKUP_FILE" | cut -f1)"
    fi
    
    # Проверяем целостность если включено
    if [ "$BACKUP_VERIFY_INTEGRITY" = "true" ]; then
        echo "🔍 Проверка целостности..."
        if [ "$BACKUP_COMPRESSION" = "true" ]; then
            if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
                echo "✅ Целостность подтверждена"
            else
                echo "❌ Ошибка целостности!"
                exit 1
            fi
        else
            echo "✅ Целостность подтверждена"
        fi
    fi
    
    # Очищаем старые бэкапы
    echo "🧹 Очистка старых бэкапов (старше $BACKUP_RETENTION_DAYS дней)..."
    if [ "$BACKUP_COMPRESSION" = "true" ]; then
        find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null
    else
        find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null
    fi
    
    echo "🎉 Операция завершена!"
else
    echo "❌ Ошибка при создании резервной копии!"
    exit 1
fi
