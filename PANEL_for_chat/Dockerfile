FROM python:3.10-slim

WORKDIR /app

# Устанавливаем системные зависимости для работы с PDF
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Открываем порт 7860
EXPOSE 7860

# Установка переменных окружения
ENV SERVER_IP=0.0.0.0
# Переменные для API ключей (заполнить при запуске или в docker-compose)
ENV MISTRAL_API_KEY=""
ENV OPENAI_API_KEY=""

CMD ["python", "front.py"] 