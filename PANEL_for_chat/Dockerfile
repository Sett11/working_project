FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Открываем порт 7860
EXPOSE 7860

# Установка переменной окружения для IP-адреса сервера
ENV SERVER_IP=0.0.0.0

CMD ["python", "front.py"] 