-- Скрипт инициализации базы данных PostgreSQL
-- Выполняется при первом запуске контейнера
-- Таблицы создаются автоматически через SQLAlchemy Base.metadata.create_all()

-- Устанавливаем расширения для мониторинга и производительности
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Настраиваем параметры для оптимальной производительности
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET log_statement = 'none';
ALTER SYSTEM SET log_min_duration_statement = 3000;
ALTER SYSTEM SET log_connections = off;
ALTER SYSTEM SET log_disconnections = off;
ALTER SYSTEM SET log_min_messages = warning;

-- Настраиваем параметры автовакуума
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 3;
ALTER SYSTEM SET autovacuum_naptime = 60;
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;
ALTER SYSTEM SET autovacuum_analyze_threshold = 50;

-- Настраиваем параметры WAL для репликации
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET wal_keep_size = '1GB';

-- Применяем изменения
SELECT pg_reload_conf();

-- Выводим информацию о созданной базе данных
SELECT 
    'Database initialized successfully' as status,
    current_database() as database_name,
    current_user as current_user,
    version() as postgres_version;
