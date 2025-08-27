#!/usr/bin/env bash

# Скрипт инициализации для запуска seeder только при создании контейнера
# Этот скрипт будет выполняться один раз при создании контейнера

echo "🚀 Инициализация контейнера..."

# Проверяем, существует ли файл-флаг, указывающий на то, что seeder уже был запущен
FLAG_FILE="/app/.seeder_flag"

# Функция для проверки готовности базы данных
wait_for_database() {
    # Проверяем наличие необходимых инструментов и переменных окружения
    if ! command -v pg_isready >/dev/null 2>&1; then
        echo "❌ Ошибка: pg_isready не найден. Убедитесь, что PostgreSQL клиент установлен."
        return 1
    fi
    
    if [ -z "$DATABASE_URL" ]; then
        echo "❌ Ошибка: DATABASE_URL не установлен."
        return 1
    fi
    
    # Используем синхронный URL для проверки готовности
    SYNC_URL="${DATABASE_URL_SYNC:-$DATABASE_URL}"
    echo "🔍 Используем URL для проверки: $SYNC_URL"
    
    # Используем переменные без local для POSIX совместимости
    db_timeout=${DB_TIMEOUT:-60}  # Таймаут по умолчанию 60 секунд
    db_interval=${DB_INTERVAL:-2}  # Интервал проверки по умолчанию 2 секунды
    db_elapsed=0
    
    echo "⏳ Ожидание готовности базы данных (таймаут: ${db_timeout}с)..."
    echo "🔍 Проверка подключения к PostgreSQL используя DATABASE_URL"
    
    # Парсим синхронный URL для получения параметров подключения
    # Формат: postgresql://user:password@host:port/database
    db_host=$(echo "$SYNC_URL" | sed -n 's/.*@\([^:]*\).*/\1/p')
    db_port=$(echo "$SYNC_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    db_name=$(echo "$SYNC_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    
    # Если не удалось распарсить, используем значения по умолчанию
    db_host=${db_host:-localhost}
    db_port=${db_port:-5432}
    db_name=${db_name:-postgres}
    
    echo "🔍 Подключение к БД: $db_host:$db_port/$db_name"
    
    # Используем pg_isready с отдельными параметрами
    while [ $db_elapsed -lt $db_timeout ]; do
        if pg_isready -h "$db_host" -p "$db_port" -d "$db_name" >/dev/null 2>&1; then
            echo "✅ База данных готова к подключению"
            return 0
        fi
        
        # Альтернативная проверка через psql
        if command -v psql >/dev/null 2>&1; then
            if psql "$SYNC_URL" -c "SELECT 1;" >/dev/null 2>&1; then
                echo "✅ База данных готова к подключению (проверка через psql)"
                return 0
            fi
        fi
        
        sleep $db_interval
        db_elapsed=$((db_elapsed + db_interval))
        echo "⏳ Ожидание... (${db_elapsed}/${db_timeout}с)"
    done
    
    echo "❌ Таймаут ожидания готовности базы данных"
    return 1
}

# Функция для проверки существования флага
check_flag_exists() {
    if [ -f "$FLAG_FILE" ]; then
        return 0  # Флаг-файл существует
    elif [ -d "$FLAG_FILE" ] && [ -f "$FLAG_FILE/.seeder_completed" ]; then
        return 0  # Директория существует и содержит маркерный файл
    fi
    return 1  # Флаг не найден
}

# Функция для создания флага
create_flag() {
    if [ -d "$FLAG_FILE" ]; then
        # Если FLAG_FILE - это директория, создаем маркерный файл внутри
        touch "$FLAG_FILE/.seeder_completed"
        echo "📝 Создан маркерный файл: $FLAG_FILE/.seeder_completed"
    else
        # Если FLAG_FILE - это файл, создаем его
        touch "$FLAG_FILE"
        echo "📝 Создан файл-флаг: $FLAG_FILE"
    fi
}

if ! check_flag_exists; then
    echo "🌱 Запуск seeder для инициализации базы данных..."
    
    # Ждем готовности базы данных
    if ! wait_for_database; then
        echo "❌ Не удалось дождаться готовности базы данных"
        exit 1
    fi
    
    # Запускаем seeder
    cd /app
    python -m db.seeder
    
    if [ $? -eq 0 ]; then
        echo "✅ Seeder успешно завершен"
        # Создаем флаг
        create_flag
    else
        echo "❌ Ошибка при выполнении seeder"
        exit 1
    fi
else
    if [ -f "$FLAG_FILE" ]; then
        echo "✅ Seeder уже был выполнен ранее (файл-флаг найден: $FLAG_FILE)"
    else
        echo "✅ Seeder уже был выполнен ранее (маркерный файл найден: $FLAG_FILE/.seeder_completed)"
    fi
fi

echo "🎉 Инициализация завершена"
