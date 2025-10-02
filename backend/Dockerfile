# 1. Используем базовый образ Python
FROM python:3.11-slim

# 2. Устанавливаем curl для healthcheck и postgresql-client для проверки БД
RUN apt-get update && apt-get install -y curl postgresql-client && rm -rf /var/lib/apt/lists/*

# 3. Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# 4. Копируем файл с зависимостями и устанавливаем их
# Этот шаг выполняется отдельно, чтобы использовать кэширование Docker
COPY requirements.txt .
COPY pip.conf /etc/pip.conf
RUN pip install --no-cache-dir --index-url https://pypi.org/simple/ --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# 5. Копируем db модуль из корня проекта (один уровень выше)
# ВАЖНО: Этот Dockerfile находится в backend/, а db/ находится в корне
COPY ../db /app/db

# 6. Копируем все файлы backend в рабочую директорию
COPY . /app/backend

# 7. Устанавливаем PYTHONPATH для корректной работы импортов
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 8. Делаем скрипт инициализации исполняемым
RUN chmod +x /app/backend/init.sh

# 9. Открываем порт для FastAPI
EXPOSE 8000

# 10. Команда по умолчанию - запуск backend сервера
CMD ["python", "/app/backend/main.py"]

