#!/bin/bash

# Установка цветного вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Запускаем процесс развертывания чат-панели...${NC}"

# Запрашиваем API-ключи
read -p "Введите ключ API Mistral (оставьте пустым, чтобы пропустить): " MISTRAL_API_KEY
read -p "Введите ключ API OpenAI (оставьте пустым, чтобы пропустить): " OPENAI_API_KEY

# Экспортируем переменные окружения
export MISTRAL_API_KEY=$MISTRAL_API_KEY
export OPENAI_API_KEY=$OPENAI_API_KEY

# Создаем необходимые директории
mkdir -p logs
mkdir -p uploads

echo -e "${GREEN}Переменные окружения установлены.${NC}"
echo -e "${YELLOW}Останавливаем предыдущие контейнеры...${NC}"

# Останавливаем текущие контейнеры
docker-compose down

echo -e "${YELLOW}Пересобираем и запускаем контейнеры...${NC}"

# Пересобираем и запускаем
docker-compose up --build -d

echo -e "${GREEN}Готово! Чат-панель запущена на http://localhost:7860${NC}" 