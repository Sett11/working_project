#!/bin/bash

# Остановка и удаление существующих контейнеров
docker-compose down

# Удаление старых образов
docker system prune -f

# Сборка и запуск новых контейнеров
docker-compose up --build -d

# Проверка статуса контейнеров
docker-compose ps 