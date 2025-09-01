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
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Создаем пользователя для приложения (если не существует)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE USER app_user WITH PASSWORD 'app_password';
        GRANT ALL PRIVILEGES ON DATABASE form_com_offer_db TO app_user;
    END IF;
END
$$;

-- Настраиваем права доступа
GRANT CONNECT ON DATABASE form_com_offer_db TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;

-- Создаем схему для приложения
CREATE SCHEMA IF NOT EXISTS app_schema;
GRANT ALL ON SCHEMA app_schema TO app_user;

-- Настраиваем параметры автовакуума
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 3;
ALTER SYSTEM SET autovacuum_naptime = 60;
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;
ALTER SYSTEM SET autovacuum_analyze_threshold = 50;

-- Настраиваем параметры WAL
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET wal_keep_segments = 64;

-- Применяем изменения
SELECT pg_reload_conf();

-- Логируем успешную инициализацию
INSERT INTO pg_stat_statements_info (dealloc) VALUES (0) ON CONFLICT DO NOTHING;

-- Выводим информацию о созданной базе данных
SELECT 
    'Database initialized successfully' as status,
    current_database() as database_name,
    current_user as current_user,
    version() as postgres_version;
