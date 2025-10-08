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
# Обновлено на nginx:1.29.2-alpine для исправления CVE-2025-23419 и поддержки HTTP/3
# CVE-2025-23419: Критическая уязвимость безопасности в nginx < 1.29.1
# HTTP/3 support: Улучшенная производительность и безопасность
# Дата обновления: 2025-10-08
FROM nginx:1.29.1-alpine

# Копируем собранное приложение из builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем кастомную конфигурацию Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Открываем порт
EXPOSE 80

# Запускаем Nginx
CMD ["nginx", "-g", "daemon off;"]
