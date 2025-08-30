FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код экспортера и необходимые зависимости
COPY . .

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 metrics && chown -R metrics:metrics /app
USER metrics

# Экспонируем порт
EXPOSE 9091

# Запускаем сервер метрик
CMD ["python", "metrics_server.py"]
