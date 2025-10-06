#!/usr/bin/env bash

# Скрипт entrypoint для backend контейнера
# Сначала запускает init.sh для инициализации БД, затем запускает приложение

set -euo pipefail

echo "🚀 Запуск backend entrypoint..."

# Запускаем скрипт инициализации
echo "📋 Шаг 1: Инициализация базы данных"
if [ -f "/app/init.sh" ]; then
    bash /app/init.sh
else
    echo "⚠️ Предупреждение: init.sh не найден, пропускаем инициализацию"
fi

# Запускаем основное приложение
echo "📋 Шаг 2: Запуск FastAPI приложения"
exec python main.py
