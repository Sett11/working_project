# 1. Используем базовый образ Python
FROM python:3.11-slim

# 2. Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# 3. Копируем файл с зависимостями и устанавливаем их
# Этот шаг выполняется отдельно, чтобы использовать кэширование Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=100 -r requirements.txt

# 4. Копируем все остальные файлы проекта в рабочую директорию
COPY . .

# 5. Команда по умолчанию была убрана, так как она определяется
# для каждого сервиса отдельно в docker-compose.yml

