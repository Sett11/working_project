FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей и очистка
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools && \
    rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y gcc python3-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf ~/.cache/pip/*

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/logs /app/user_data /app/utils /app/steps /app/db /app/prompts && \
    chown -R botuser:botuser /app && \
    chmod -R 755 /app

# Копирование кода приложения
COPY --chown=botuser:botuser . .

# Переключение на непривилегированного пользователя
USER botuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Europe/Moscow

# Проверка работоспособности
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python bot.py" || exit 1

CMD ["python", "bot.py"]