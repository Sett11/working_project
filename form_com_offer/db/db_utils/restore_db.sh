#!/bin/bash

# Скрипт для восстановления PostgreSQL базы данных из резервной копии
# Использование: ./restore_db.sh [путь_к_файлу_бэкапа]

# Настройки из переменных окружения
DB_NAME="${POSTGRES_DB:-form_com_offer_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="/backups"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-true}"
BACKUP_VERIFY_INTEGRITY="${BACKUP_VERIFY_INTEGRITY:-true}"

# Проверяем аргументы
if [ -z "$1" ]; then
    echo "❌ Ошибка: Не указан файл резервной копии!"
    echo "Использование: $0 <путь_к_файлу_бэкапа>"
    echo "Пример: $0 /backups/backup_form_com_offer_db_20250901_151500.sql"
    exit 1
fi

BACKUP_FILE="$1"

# Проверяем существование файла бэкапа
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Файл резервной копии не найден: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  ВНИМАНИЕ: Это действие перезапишет существующую базу данных!"
echo "📁 Файл для восстановления: $BACKUP_FILE"
echo "🗄️  База данных: $DB_NAME"
echo "🔧 Настройки: сжатие=$BACKUP_COMPRESSION, проверка=$BACKUP_VERIFY_INTEGRITY"

# Запрашиваем подтверждение
read -p "Продолжить восстановление? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Восстановление отменено пользователем"
    exit 0
fi

echo "🔄 Начинаем восстановление базы данных..."

# Проверяем целостность файла если включено
if [ "$BACKUP_VERIFY_INTEGRITY" = "true" ]; then
    echo "🔍 Проверка целостности файла..."
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        if ! gunzip -t "$BACKUP_FILE" 2>/dev/null; then
            echo "❌ Ошибка целостности файла!"
            exit 1
        fi
        echo "✅ Целостность подтверждена"
    else
        echo "✅ Целостность подтверждена"
    fi
fi

# Создаем резервную копию текущей БД перед восстановлением
echo "💾 Создаем резервную копию текущей БД..."
CURRENT_BACKUP="${BACKUP_DIR}/pre_restore_backup_${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose --clean --create --if-exists \
    --file="$CURRENT_BACKUP" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Резервная копия создана: $CURRENT_BACKUP"
else
    echo "⚠️  Не удалось создать резервную копию текущей БД (возможно, БД не существует)"
fi

# Восстанавливаем БД
echo "🔄 Восстанавливаем базу данных..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "🗜️ Распаковываем сжатый файл..."
    gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" --verbose
else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" --file="$BACKUP_FILE" --verbose
fi

if [ $? -eq 0 ]; then
    echo "✅ Восстановление завершено успешно!"
    echo "🎉 База данных $DB_NAME восстановлена из файла $BACKUP_FILE"
else
    echo "❌ Ошибка при восстановлении базы данных!"
    echo "💡 Проверьте логи выше для получения дополнительной информации"
    exit 1
fi
