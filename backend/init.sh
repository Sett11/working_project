#!/usr/bin/env bash

# Строгие флаги безопасности:
# -e: выход при любой ошибке команды
# -u: выход при использовании неопределенных переменных
# -o pipefail: выход при ошибке в любой части pipeline
set -euo pipefail

# Скрипт инициализации для запуска seeder только при создании контейнера
# Этот скрипт будет выполняться один раз при создании контейнера

echo "🚀 Инициализация контейнера..."

# Проверяем, существует ли файл-флаг, указывающий на то, что seeder уже был запущен
# Путь к флагу можно переопределить через переменную окружения SEEDER_FLAG_FILE
FLAG_FILE="${SEEDER_FLAG_FILE:-/app/.seeder_flag}"
echo "🔍 Используется путь к флагу: $FLAG_FILE"

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
    db_interval=${DB_INTERVAL:-5}  # Интервал проверки по умолчанию 5 секунд
    db_elapsed=0
    
    echo "⏳ Ожидание готовности базы данных (таймаут: ${db_timeout}с)..."
    echo "🔍 Проверка подключения к PostgreSQL используя DATABASE_URL_SYNC"
    echo "🔍 URL: $SYNC_URL"
    
    # Парсим синхронный URL для получения параметров подключения
    # Формат: postgresql://user:password@host:port/database
    db_host=$(echo "$SYNC_URL" | sed -n 's/.*@\([^:]*\).*/\1/p')
    db_port=$(echo "$SYNC_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    db_name=$(echo "$SYNC_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    
    # Если не удалось распарсить, используем значения по умолчанию
    db_host=${db_host:-db}
    db_port=${db_port:-5432}
    db_name=${db_name:-form_com_offer_db}
    
    echo "🔍 Подключение к БД: $db_host:$db_port/$db_name"
    
    # Даем БД время на полную инициализацию
    echo "⏳ Начальная задержка для инициализации БД..."
    sleep 15
    
    # Простая проверка через psql
    while [ $db_elapsed -lt $db_timeout ]; do
        if command -v psql >/dev/null 2>&1; then
            if psql "$SYNC_URL" -c "SELECT 1;" >/dev/null 2>&1; then
                echo "✅ База данных готова к подключению"
                return 0
            fi
        fi
        
        # Дополнительная проверка через netcat (если доступен)
        if command -v nc >/dev/null 2>&1; then
            if nc -z "$db_host" "$db_port" 2>/dev/null; then
                echo "✅ Порт $db_port на $db_host доступен (netcat)"
                # Если порт доступен, но pg_isready не работает, даем БД еще время
                sleep 2
                continue
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
    fi
    
    if [ -d "$FLAG_FILE" ] && [ -f "$FLAG_FILE/.seeder_completed" ]; then
        return 0  # Директория существует и содержит маркерный файл
    fi
    
    return 1  # Флаг не найден
}

# Функция для создания флага
create_flag() {
    local target_file
    
    if [ -d "$FLAG_FILE" ]; then
        # Если FLAG_FILE - это директория, создаем маркерный файл внутри
        target_file="$FLAG_FILE/.seeder_completed"
    else
        # Если FLAG_FILE - это файл, создаем его
        target_file="$FLAG_FILE"
    fi
    
    # Пытаемся создать файл-флаг и проверяем успешность операции
    if ! touch "$target_file" 2>/dev/null; then
        echo "❌ Ошибка: не удалось создать файл-флаг $target_file" >&2
        return 1
    fi
    
    # Проверяем, что файл действительно был создан
    if [ ! -f "$target_file" ]; then
        echo "❌ Ошибка: файл-флаг $target_file не существует после создания" >&2
        return 1
    fi
    
    echo "📝 Создан файл-флаг: $target_file"
    return 0
}

# Путь к файлу блокировки для предотвращения одновременного выполнения seeder
LOCK_FILE="${SEEDER_LOCK_FILE:-/app/.seeder.lock}"
echo "🔍 Используется файл блокировки: $LOCK_FILE"

# Функция для безопасного перехода в рабочую директорию
safe_cd() {
    local target_dir="$1"
    
    # Проверяем существование директории
    if [ ! -d "$target_dir" ]; then
        echo "❌ Ошибка: директория $target_dir не существует" >&2
        return 1
    fi
    
    # Пытаемся перейти в директорию
    if ! cd "$target_dir" 2>/dev/null; then
        echo "❌ Ошибка: не удалось перейти в директорию $target_dir" >&2
        return 1
    fi
    
    echo "✅ Успешно перешли в директорию: $target_dir"
    return 0
}

# Открываем файл блокировки и захватываем эксклюзивную блокировку
# Файловый дескриптор 200 используется для блокировки
exec 200>"$LOCK_FILE"

echo "🔒 Попытка захвата блокировки..."

# Пытаемся захватить эксклюзивную блокировку (неблокирующий режим)
if ! flock -n 200; then
    echo "⏳ Другой контейнер уже выполняет seeder. Ожидание..."
    # Захватываем блокировку в блокирующем режиме (ждем освобождения)
    if ! flock -w 300 200; then
        echo "❌ Не удалось захватить блокировку в течение 300 секунд" >&2
        exit 1
    fi
fi

echo "✅ Блокировка захвачена"

# Внутри блокировки проверяем флаг повторно (другой контейнер мог его создать)
if ! check_flag_exists; then
    echo "🌱 Запуск seeder для инициализации базы данных..."
    
    # Ждем готовности базы данных
    if ! wait_for_database; then
        echo "❌ Не удалось дождаться готовности базы данных" >&2
        # Освобождаем блокировку перед выходом
        flock -u 200
        exit 1
    fi
    
    # Безопасно переходим в рабочую директорию
    if ! safe_cd /app; then
        echo "❌ Не удалось перейти в рабочую директорию" >&2
        # Освобождаем блокировку перед выходом
        flock -u 200
        exit 1
    fi
    
    # Запускаем seeder
    echo "🚀 Запуск python -m db.seeder..."
    if python -m db.seeder; then
        echo "✅ Seeder успешно завершен"
        
        # Создаем флаг и проверяем успешность
        if ! create_flag; then
            echo "❌ Не удалось создать файл-флаг после успешного выполнения seeder" >&2
            # Освобождаем блокировку перед выходом
            flock -u 200
            exit 1
        fi
    else
        echo "❌ Ошибка при выполнении seeder (код выхода: $?)" >&2
        # Освобождаем блокировку перед выходом
        flock -u 200
        exit 1
    fi
else
    if [ -f "$FLAG_FILE" ]; then
        echo "✅ Seeder уже был выполнен ранее (файл-флаг найден: $FLAG_FILE)"
    else
        echo "✅ Seeder уже был выполнен ранее (маркерный файл найден: $FLAG_FILE/.seeder_completed)"
    fi
fi

# Освобождаем блокировку
echo "🔓 Освобождение блокировки..."
flock -u 200

echo "🎉 Инициализация завершена"
