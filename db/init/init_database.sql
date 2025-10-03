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
-- Логирование запросов: 'ddl' - логирует изменения схемы (CREATE, ALTER, DROP)
-- Это обеспечивает аудит критических операций для compliance и безопасности.
-- Альтернативы: 'mod' - DDL + изменения данных (INSERT/UPDATE/DELETE), 'all' - все запросы
-- Примечание: Для продакшена рекомендуется дополнительный мониторинг через:
-- - APM системы (например, pg_stat_monitor, pgBadger)
-- - Query monitoring инструменты
-- - Централизованное логирование с ротацией и retention policy
ALTER SYSTEM SET log_statement = 'ddl';
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

-- Предоставляем права на схему приложения (ТОЛЬКО USAGE, без CREATE для безопасности)
GRANT USAGE ON SCHEMA app_schema TO app_user;

-- ВАЖНО: DDL операции (CREATE, ALTER, DROP) должны выполняться отдельным миграционным
-- пользователем или администратором БД в рамках контролируемого процесса деплоя.
-- app_user получает ТОЛЬКО DML привилегии для работы с данными:

-- Предоставляем DML права на все существующие таблицы в app_schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app_schema TO app_user;
-- Предоставляем права на последовательности (для SERIAL/BIGSERIAL колонок)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app_schema TO app_user;

-- Настраиваем права по умолчанию для будущих таблиц и последовательностей
-- (применяется к объектам, созданным после выполнения этого скрипта)
-- FOR ROLE postgres указывает, что права применяются к объектам, создаваемым ролью postgres
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA app_schema GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA app_schema GRANT USAGE, SELECT ON SEQUENCES TO app_user;

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
-- ALTER SYSTEM SET wal_keep_size = '64MB';  -- Используем современный параметр вместо устаревшего wal_keep_segments
-- 
-- Примечание: wal_keep_size актуален только при включенной репликации и определяет
-- минимальный объем WAL файлов, которые нужно хранить для реплик.
-- Без репликации этот параметр не используется и не должен быть установлен.

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

-- Проверяем конфигурацию pg_stat_statements
-- ВАЖНО: Эта проверка определяет, настроена ли библиотека в shared_preload_libraries,
-- но НЕ проверяет runtime доступность (которая требует перезапуска PostgreSQL).
-- После перезапуска сервера extension станет полностью функциональной.
SELECT 
    CASE 
        WHEN setting LIKE '%pg_stat_statements%' 
        THEN 'pg_stat_statements: CONFIGURED (restart required to activate)'
        ELSE 'pg_stat_statements: NOT CONFIGURED'
    END as configuration_status,
    setting as current_value
FROM pg_settings 
WHERE name = 'shared_preload_libraries';

-- Логируем успешную инициализацию в нашу таблицу
INSERT INTO app_schema.initialization_log (status, postgres_version, user_id)
VALUES ('Database initialized successfully', version(), 'root_app');

-- Выводим информацию о созданной базе данных
SELECT 
    'Database initialized successfully' as status,
    current_database() as database_name,
    current_user as current_user,
    version() as postgres_version;
