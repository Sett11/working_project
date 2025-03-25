#!/bin/bash

# Остановка и удаление существующего контейнера, если он существует
docker stop chat_panel || true
docker rm chat_panel || true

# Удаление образа, если он существует
docker rmi chat_panel:latest || true

# Сборка нового образа
docker build -t chat_panel:latest .

# Запуск контейнера
docker run -d --name chat_panel \
  -p 7860:7860 \
  -e SERVER_IP=86.110.212.192 \
  --restart always \
  chat_panel:latest

# Проверка статуса контейнера
docker ps -a | grep chat_panel 