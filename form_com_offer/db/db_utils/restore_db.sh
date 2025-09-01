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

# Определяем user_id для логирования (по умолчанию 'root_app' для системных операций)
USER_ID="${USER_ID:-root_app}"

# Функция логирования с user_id
log_message() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - user_id=${USER_ID} | [RESTORE] ${level}: ${message}"
}

# Проверяем аргументы
if [ -z "$1" ]; then
    log_message "ERROR" "❌ Ошибка: Не указан файл резервной копии!"
    log_message "ERROR" "Использование: $0 <путь_к_файлу_бэкапа>"
    log_message "ERROR" "Пример: $0 /backups/backup_form_com_offer_db_20250901_151500.sql"
    exit 1
fi

BACKUP_FILE="$1"

# Проверяем существование файла бэкапа
if [ ! -f "$BACKUP_FILE" ]; then
    log_message "ERROR" "❌ Файл резервной копии не найден: $BACKUP_FILE"
    exit 1
fi

# Проверяем директорию для бэкапов и права на запись
if [ ! -d "$BACKUP_DIR" ]; then
    log_message "ERROR" "❌ Директория для бэкапов не существует: $BACKUP_DIR"
    exit 1
fi

if [ ! -w "$BACKUP_DIR" ]; then
    log_message "ERROR" "❌ Нет прав на запись в директорию: $BACKUP_DIR"
    exit 1
fi

log_message "WARN" "⚠️  ВНИМАНИЕ: Это действие перезапишет существующую базу данных!"
log_message "INFO" "📁 Файл для восстановления: $BACKUP_FILE"
log_message "INFO" "🗄️  База данных: $DB_NAME"
log_message "INFO" "🔧 Настройки: сжатие=$BACKUP_COMPRESSION, проверка=$BACKUP_VERIFY_INTEGRITY"

# Запрашиваем подтверждение
read -p "Продолжить восстановление? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_message "INFO" "❌ Восстановление отменено пользователем"
    exit 0
fi

log_message "INFO" "🔄 Начинаем восстановление базы данных..."

# Проверяем целостность файла если включено
if [ "$BACKUP_VERIFY_INTEGRITY" = "true" ]; then
    log_message "INFO" "🔍 Проверка целостности файла..."
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        if ! gunzip -t "$BACKUP_FILE" 2>/dev/null; then
            log_message "ERROR" "❌ Ошибка целостности файла!"
            exit 1
        fi
        log_message "INFO" "✅ Целостность подтверждена"
    else
        log_message "INFO" "✅ Целостность подтверждена"
    fi
fi

# Создаем резервную копию текущей БД перед восстановлением
log_message "INFO" "💾 Создаем резервную копию текущей БД..."
CURRENT_BACKUP="${BACKUP_DIR}/pre_restore_backup_${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"

# Выполняем pg_dump и захватываем код выхода
log_message "INFO" "📤 Создание резервной копии текущей БД..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose --clean --create --if-exists \
    --file="$CURRENT_BACKUP"
PG_DUMP_EXIT_CODE=$?

# Проверяем успешность выполнения pg_dump
if [ $PG_DUMP_EXIT_CODE -ne 0 ]; then
    log_message "ERROR" "❌ Ошибка при создании резервной копии текущей БД!"
    log_message "ERROR" "💡 Код выхода pg_dump: $PG_DUMP_EXIT_CODE"
    log_message "ERROR" "💡 Проверьте подключение к БД и права доступа"
    exit 1
fi

# Проверяем существование созданного файла
if [ ! -f "$CURRENT_BACKUP" ]; then
    log_message "ERROR" "❌ Критическая ошибка: Файл резервной копии не был создан!"
    log_message "ERROR" "💡 Ожидаемый файл: $CURRENT_BACKUP"
    log_message "ERROR" "💡 Проверьте права на запись в директорию $BACKUP_DIR"
    exit 1
fi

# Проверяем размер файла (должен быть больше 0)
if [ ! -s "$CURRENT_BACKUP" ]; then
    log_message "ERROR" "❌ Критическая ошибка: Созданный файл резервной копии пуст!"
    echo "💡 Файл: $CURRENT_BACKUP"
    echo "💡 Размер файла: $(stat -c%s "$CURRENT_BACKUP" 2>/dev/null || echo 'неизвестен') байт"
    echo "💡 Возможно, база данных пуста или возникла ошибка при создании бэкапа"
    exit 1
fi

log_message "INFO" "✅ Резервная копия создана успешно: $CURRENT_BACKUP"
log_message "INFO" "💾 Размер файла: $(stat -c%s "$CURRENT_BACKUP" 2>/dev/null || echo 'неизвестен') байт"

# Восстанавливаем БД
log_message "INFO" "🔄 Восстанавливаем базу данных..."
RESTORE_EXIT_CODE=0

if [[ "$BACKUP_FILE" == *.gz ]]; then
    log_message "INFO" "🗜️ Распаковываем сжатый файл..."
    gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" --verbose
    RESTORE_EXIT_CODE=${PIPESTATUS[1]}  # Получаем код выхода psql из пайпа
else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" --file="$BACKUP_FILE" --verbose
    RESTORE_EXIT_CODE=$?
fi

# Проверяем результат восстановления
if [ $RESTORE_EXIT_CODE -eq 0 ]; then
    log_message "INFO" "✅ Восстановление завершено успешно!"
    log_message "INFO" "🎉 База данных $DB_NAME восстановлена из файла $BACKUP_FILE"
    log_message "INFO" "💾 Резервная копия предыдущего состояния сохранена в: $CURRENT_BACKUP"
else
    log_message "ERROR" "❌ Критическая ошибка при восстановлении базы данных!"
    log_message "ERROR" "💡 Код выхода: $RESTORE_EXIT_CODE"
    log_message "ERROR" "💡 Проверьте логи выше для получения дополнительной информации"
    log_message "ERROR" "💡 Возможно, файл бэкапа поврежден или несовместим с текущей версией PostgreSQL"
    log_message "INFO" "💾 Резервная копия предыдущего состояния сохранена в: $CURRENT_BACKUP"
    exit 1
fi
