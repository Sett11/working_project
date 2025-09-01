#!/bin/bash

# Скрипт для мониторинга состояния PostgreSQL базы данных
# Использование: ./monitor_db.sh

# Настройки из переменных окружения
DB_NAME="${POSTGRES_DB:-form_com_offer_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
MONITORING_ENABLED="${MONITORING_ENABLED:-true}"
MONITORING_INTERVAL="${MONITORING_INTERVAL:-300}"
MONITORING_LOG_QUERIES="${MONITORING_LOG_QUERIES:-true}"

echo "🔍 Мониторинг состояния базы данных $DB_NAME"
echo "================================================"
echo "🔧 Настройки: мониторинг=$MONITORING_ENABLED, интервал=${MONITORING_INTERVAL}с"

# Проверяем подключение к БД
echo "📡 Проверка подключения к БД..."
if pg_isready -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" >/dev/null 2>&1; then
    echo "✅ Подключение к БД успешно"
else
    echo "❌ Ошибка подключения к БД"
    exit 1
fi

# Получаем информацию о размере БД
echo ""
echo "📊 Информация о размере БД:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT 
    pg_size_pretty(pg_database_size('$DB_NAME')) as database_size,
    pg_size_pretty(pg_total_relation_size('clients')) as clients_table_size,
    pg_size_pretty(pg_total_relation_size('orders')) as orders_table_size,
    pg_size_pretty(pg_total_relation_size('air_conditioners')) as air_conditioners_table_size,
    pg_size_pretty(pg_total_relation_size('components')) as components_table_size;
"

# Получаем статистику подключений
echo ""
echo "🔗 Статистика подключений:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT 
    count(*) as active_connections,
    max_conn as max_connections,
    round((count(*)::float / max_conn::float) * 100, 2) as connection_usage_percent
FROM pg_stat_activity, (SELECT setting::int as max_conn FROM pg_settings WHERE name = 'max_connections') as max_conn
WHERE state = 'active';
"

# Получаем информацию о медленных запросах (если включено)
if [ "$MONITORING_LOG_QUERIES" = "true" ]; then
    echo ""
    echo "🐌 Медленные запросы (последние 10):"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT 
        query,
        calls,
        total_time,
        mean_time,
        rows
    FROM pg_stat_statements 
    WHERE query NOT LIKE '%pg_stat_statements%'
    ORDER BY mean_time DESC 
    LIMIT 10;
    "
fi

# Получаем информацию о блокировках
echo ""
echo "🔒 Активные блокировки:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT 
    locktype,
    database,
    relation::regclass,
    mode,
    granted
FROM pg_locks 
WHERE NOT granted OR locktype != 'relation';
"

# Получаем информацию о вакууме
echo ""
echo "🧹 Статистика автовакуума:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT 
    schemaname,
    tablename,
    last_vacuum,
    last_autovacuum,
    vacuum_count,
    autovacuum_count
FROM pg_stat_user_tables 
WHERE autovacuum_count > 0
ORDER BY autovacuum_count DESC 
LIMIT 5;
"

# Получаем информацию о дисковом пространстве
echo ""
echo "💾 Использование дискового пространства:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC 
LIMIT 10;
"

# Получаем информацию о настройках PostgreSQL
echo ""
echo "⚙️ Текущие настройки PostgreSQL:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT 
    name,
    setting,
    unit,
    context
FROM pg_settings 
WHERE name IN ('max_connections', 'shared_buffers', 'effective_cache_size', 'work_mem', 'autovacuum_max_workers')
ORDER BY name;
"

echo ""
echo "✅ Мониторинг завершен"
