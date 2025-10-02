-- Скрипт инициализации базы данных PostgreSQL
-- Выполняется при первом запуске контейнера

-- Создаем базу данных, если она не существует
SELECT 'CREATE DATABASE form_com_offer_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'form_com_offer_db')\gexec

-- Подключаемся к созданной базе данных
\c form_com_offer_db;

-- Устанавливаем расширения для мониторинга и производительности
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Настраиваем параметры для лучшей производительности
-- ВАЖНО: Изменение shared_preload_libraries требует перезапуска PostgreSQL!
-- Этот скрипт НЕ выполняет перезапуск автоматически.
-- Оператор должен вручную перезапустить сервер для применения pg_stat_statements.
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
-- Безопасное логирование: 'none' - не логировать запросы (рекомендуется для продакшена)
-- Альтернативы: 'ddl' - только DDL, 'mod' - DDL и изменения данных
ALTER SYSTEM SET log_statement = 'none';
-- Логирование медленных запросов (более 1000 мс)
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Создаем пользователя для приложения (если не существует)
-- ВАЖНО: Пароль должен быть передан через переменную окружения при запуске скрипта:
-- psql -v APP_USER_PASSWORD="'your_secure_password'" -f init_database.sql
-- или через docker-compose с переменной окружения
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE USER app_user WITH PASSWORD :'APP_USER_PASSWORD';
    END IF;
END
$$;

-- Настраиваем минимальные необходимые права доступа (принцип наименьших привилегий)
GRANT CONNECT ON DATABASE form_com_offer_db TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
-- Не предоставляем CREATE на public схему для безопасности

-- Создаем схему для приложения
CREATE SCHEMA IF NOT EXISTS app_schema;
-- Предоставляем права на схему приложения
GRANT USAGE ON SCHEMA app_schema TO app_user;
GRANT CREATE ON SCHEMA app_schema TO app_user;
-- После создания таблиц в app_schema необходимо явно предоставить права:
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app_schema TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app_schema TO app_user;

-- Настраиваем параметры автовакуума
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 3;
ALTER SYSTEM SET autovacuum_naptime = 60;
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;
ALTER SYSTEM SET autovacuum_analyze_threshold = 50;

-- Настраиваем параметры WAL
-- ВАЖНО: Параметры репликации закомментированы, так как репликация не требуется.
-- Раскомментируйте только если настраиваете репликацию:
-- ALTER SYSTEM SET wal_level = replica;
-- ALTER SYSTEM SET max_wal_senders = 3;
-- Используем современный параметр wal_keep_size вместо устаревшего wal_keep_segments
ALTER SYSTEM SET wal_keep_size = '64MB';

-- Создаем таблицу для логирования инициализации в нашей схеме
CREATE TABLE IF NOT EXISTS app_schema.initialization_log (
    id SERIAL PRIMARY KEY,
    initialized_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    postgres_version TEXT,
    status TEXT,
    user_id TEXT DEFAULT 'root_app'
);

-- Предоставляем права на таблицу логирования
GRANT SELECT, INSERT ON app_schema.initialization_log TO app_user;
GRANT USAGE, SELECT ON SEQUENCE app_schema.initialization_log_id_seq TO app_user;

-- Применяем изменения конфигурации
SELECT pg_reload_conf();

-- Проверяем работоспособность pg_stat_statements
-- (это read-only проверка, не пытаемся писать в системные view)
SELECT 
    'pg_stat_statements extension verified' as verification_status,
    count(*) as statements_count 
FROM pg_stat_statements;

-- Логируем успешную инициализацию в нашу таблицу
INSERT INTO app_schema.initialization_log (status, postgres_version, user_id)
VALUES ('Database initialized successfully', version(), 'root_app');

-- Выводим информацию о созданной базе данных
SELECT 
    'Database initialized successfully' as status,
    current_database() as database_name,
    current_user as current_user,
    version() as postgres_version;
