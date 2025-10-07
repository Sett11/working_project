# Multi-stage build для оптимизации размера образа

# Этап 1: Сборка приложения
FROM node:20-alpine AS builder

# Принимаем build argument
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

WORKDIR /app

# Копируем файлы зависимостей
COPY package*.json ./

# Устанавливаем ВСЕ зависимости (включая devDependencies для сборки)
# Для Alpine Linux с Rollup нужны все опциональные зависимости
RUN npm ci && npm cache clean --force

# Копируем исходный код
COPY . .

# Собираем production build
RUN npm run build

# Этап 2: Production образ с Nginx
FROM nginx:1.27-alpine

# Копируем собранное приложение из builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем кастомную конфигурацию Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Открываем порт
EXPOSE 80

# Запускаем Nginx
CMD ["nginx", "-g", "daemon off;"]
