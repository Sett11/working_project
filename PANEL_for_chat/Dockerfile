# Используем базовый образ Python
FROM python:3.11-slim

RUN apt-get update && apt-get upgrade -y

RUN pip install pip -U

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файлы requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта в контейнер
COPY . .

# Указываем порт, который будет использоваться приложением
EXPOSE 7860

# Команда для запуска приложения
CMD ["python", "front.py"]
