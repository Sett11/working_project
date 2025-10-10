# 1. Используем базовый образ Python
FROM python:3.11-slim

# 2. Устанавливаем curl для healthcheck и postgresql-client для проверки БД
RUN apt-get update \
    && apt-get install -y curl postgresql-client \
    && apt-get install -y --only-upgrade curl openssl libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# 4. Копируем файл с зависимостями и устанавливаем их
# Этот шаг выполняется отдельно, чтобы использовать кэширование Docker
COPY requirements.txt .
COPY pip.conf /etc/pip.conf
RUN python -m pip install --upgrade --no-cache-dir pip setuptools \
    && pip install --no-cache-dir --index-url https://pypi.org/simple/ --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# 4. Копируем все остальные файлы проекта в рабочую директорию
COPY . .

# 5. Делаем скрипты исполняемыми
RUN chmod +x init.sh entrypoint.sh

# 6. Устанавливаем entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

