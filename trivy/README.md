# 🛡️ Trivy Security Scanner - Документация

## 📋 Оглавление

- [О проекте](#о-проекте)
- [Быстрый старт](#быстрый-старт)
- [Установка](#установка)
- [Использование](#использование)
- [Структура файлов](#структура-файлов)
- [Конфигурация](#конфигурация)
- [Интерпретация результатов](#интерпретация-результатов)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## 🔍 О проекте

**Trivy** — это комплексный open-source сканер безопасности от Aqua Security, который помогает обнаруживать:

- 🐛 **Уязвимости** в Docker образах, пакетах ОС и языковых библиотеках
- ⚙️ **Неправильные конфигурации** (IaC, Docker, Kubernetes)
- 🔐 **Утечки секретов** (пароли, API ключи, токены)
- 📜 **Лицензии** библиотек и пакетов

### Почему Trivy?

- ✅ Быстрый и легковесный
- ✅ Не требует установки агентов
- ✅ Регулярно обновляемая база уязвимостей
- ✅ Поддержка множества форматов отчётов
- ✅ Интеграция с CI/CD

---

## 🚀 Быстрый старт

### Предварительные требования

- ✅ **Docker Desktop** установлен и запущен
- ✅ **PowerShell** (встроен в Windows)
- ✅ **Docker образы** собраны (Backend, Frontend, DB)

### Запуск сканирования за 30 секунд

```powershell
# 1. Перейдите в директорию trivy
cd trivy

# 2. Запустите сканирование всех образов
.\scan-all.ps1
```

**Вот и всё!** 🎉 Результаты сохранятся в `trivy/reports/`

---

## 📦 Установка

### Вариант 1: Использование Docker (Рекомендуется)

Trivy уже настроен через Docker! Скрипты автоматически загружают образ при первом запуске.

```powershell
# Образ загрузится автоматически при первом сканировании
.\scan-all.ps1
```

### Вариант 2: Локальная установка Trivy (Опционально)

Если хотите использовать Trivy напрямую без Docker:

#### Windows

1. Скачайте [Trivy для Windows](https://github.com/aquasecurity/trivy/releases/latest)
2. Распакуйте `trivy.exe` в директорию, добавленную в PATH
3. Проверьте установку:

```powershell
trivy --version
```

#### Альтернативно через Scoop

```powershell
scoop install trivy
```

---

## 💻 Использование

### Основные команды

#### 1️⃣ Сканирование всех образов

```powershell
cd trivy
.\scan-all.ps1
```

**Что делает:**
- ✅ Сканирует Backend образ
- ✅ Сканирует Frontend образ (если собран)
- ✅ Сканирует Database образ (postgres:15-alpine)
- 📊 Генерирует итоговый отчёт

#### 2️⃣ Сканирование только Backend

```powershell
cd trivy
.\scan-backend.ps1
```

#### 3️⃣ Сканирование только Frontend

```powershell
cd trivy
.\scan-frontend.ps1
```

**Примечание:** Frontend образ создаётся только перед финальным деплоем:

```powershell
# Сначала соберите образ
cd ..
docker-compose build frontend

# Затем просканируйте
cd trivy
.\scan-frontend.ps1
```

### Использование через Docker Compose

```powershell
# Интерактивное сканирование образа
docker-compose -f trivy/docker-compose.trivy.yml run --rm trivy-scan image your_image_name:tag

# Пример: сканирование backend
docker-compose -f trivy/docker-compose.trivy.yml run --rm trivy-scan image working_project_backend
```

---

## 📁 Структура файлов

```
trivy/
├── 📄 README.md                    # Эта документация
├── 🐳 docker-compose.trivy.yml     # Docker Compose конфигурация
├── ⚙️ trivy-config.yaml            # Конфигурация Trivy
│
├── 📜 Скрипты PowerShell:
│   ├── scan-all.ps1                # Сканирование всех образов
│   ├── scan-backend.ps1            # Только Backend
│   └── scan-frontend.ps1           # Только Frontend
│
├── 📊 reports/                     # Отчёты сканирования
│   ├── scan_backend_*.json
│   ├── scan_backend_*.txt
│   ├── scan_frontend_*.json
│   ├── scan_frontend_*.txt
│   └── summary_*.txt               # Итоговый отчёт
│
└── 📝 logs/                        # Логи сканирования
```

---

## ⚙️ Конфигурация

### Файл `trivy-config.yaml`

Основные настройки сканирования:

```yaml
scan:
  scanners:
    - vuln        # Уязвимости
    - misconfig   # Конфигурации
    - secret      # Секреты
  
  severity:
    - CRITICAL    # Критические
    - HIGH        # Высокие
    - MEDIUM      # Средние
```

### Игнорирование уязвимостей

Отредактируйте файл `.trivyignore` в корне проекта:

```bash
# Игнорировать конкретную CVE
CVE-2023-12345

# С комментарием
CVE-2023-67890 # Принят риск после security review

# С датой истечения
CVE-2024-11111 exp:2025-12-31 # Ждём патч
```

### Настройка уровней важности

Отредактируйте `scan-all.ps1`:

```powershell
# Изменить строку:
--severity CRITICAL,HIGH,MEDIUM

# На более строгую:
--severity CRITICAL
```

---

## 📊 Интерпретация результатов

### Уровни важности

| Уровень | Значение | Действие |
|---------|----------|----------|
| 🔴 **CRITICAL** | Критические уязвимости | ❗ Немедленное исправление обязательно |
| 🟠 **HIGH** | Высокий риск | ⚠️ Исправить в ближайшее время (1-7 дней) |
| 🟡 **MEDIUM** | Средний риск | 📅 Запланировать исправление (1-4 недели) |
| 🔵 **LOW** | Низкий риск | 📝 Отслеживать, исправить при возможности |

### Пример отчёта

```
Backend (working_project_backend)
--------------------------------------------------------------------------------
Статус: Completed
Уязвимости:
  🔴 CRITICAL: 2
  🟠 HIGH:     5
  🟡 MEDIUM:   12
  🔵 LOW:      20
```

**Что делать:**
1. Откройте детальный отчёт: `reports/scan_backend_*.txt`
2. Найдите уязвимости CRITICAL и HIGH
3. Обновите уязвимые пакеты в `requirements.txt` или `package.json`
4. Пересоберите образ: `docker-compose build backend`
5. Повторите сканирование

### Типичные проблемы и решения

#### Уязвимость в базовом образе (Python, Node, Alpine)

```dockerfile
# ❌ Плохо
FROM python:3.9-slim

# ✅ Хорошо - используйте конкретную версию
FROM python:3.9.18-slim
```

#### Уязвимые зависимости Python

```bash
# Обновите requirements.txt
pip list --outdated
pip install --upgrade package-name==new-version
```

#### Уязвимые зависимости Node.js

```bash
# Проверьте обновления
npm outdated

# Обновите пакеты
npm update package-name
```

---

## 🔧 Troubleshooting

### Проблема: "Docker не найден"

```powershell
✗ Docker не найден! Установите Docker Desktop.
```

**Решение:**
1. Установите [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Запустите Docker Desktop
3. Проверьте: `docker --version`

### Проблема: "Образ не найден"

```powershell
⚠ Образ 'working_project_backend' не найден. Пропускаем...
```

**Решение:**

```powershell
# Соберите образ
docker-compose build backend

# Проверьте наличие
docker images | grep working_project
```

### Проблема: Frontend не сканируется

**Это нормально!** Frontend образ создаётся только перед деплоем.

**Когда нужно просканировать Frontend:**

```powershell
# 1. Соберите образ
docker-compose build frontend

# 2. Запустите сканирование
cd trivy
.\scan-frontend.ps1
```

### Проблема: Медленное сканирование

**Причина:** Загрузка базы данных уязвимостей при первом запуске.

**Решение:**
- Подождите ~1-2 минуты при первом запуске
- Последующие сканирования будут быстрее (база кэшируется)

### Проблема: Слишком много уязвимостей

**Нормально!** Даже официальные образы могут иметь уязвимости.

**Что делать:**
1. Фокусируйтесь на CRITICAL и HIGH
2. Используйте `.trivyignore` для принятых рисков
3. Регулярно обновляйте образы и зависимости

---

## 🎯 Best Practices

### 1. Регулярное сканирование

```powershell
# Запускайте сканирование:
# ✅ После обновления зависимостей
# ✅ После изменения Dockerfile
# ✅ Перед деплоем в production
# ✅ Еженедельно как часть security audit
```

### 2. Используйте конкретные версии

```dockerfile
# ❌ Плохо - floating tags
FROM nginx:alpine
FROM python:3.9

# ✅ Хорошо - точные версии
FROM nginx:1.29.1-alpine
FROM python:3.9.18-slim
```

### 3. Минимизируйте базовые образы

```dockerfile
# ✅ Используйте slim/alpine версии
FROM python:3.9-slim
FROM node:20-alpine
```

### 4. Multi-stage builds

```dockerfile
# ✅ Оставляйте только необходимое в финальном образе
FROM node:20-alpine AS builder
# ... build steps ...

FROM nginx:1.29.1-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

### 5. Автоматизация

#### Добавьте в Git hooks

Создайте `.git/hooks/pre-commit`:

```bash
#!/bin/bash
cd trivy
powershell -ExecutionPolicy Bypass -File scan-all.ps1
```

#### Запуск по расписанию (Windows Task Scheduler)

```powershell
# Создайте задачу, которая запускает scan-all.ps1 каждую неделю
```

### 6. Документируйте исключения

```bash
# .trivyignore
CVE-2023-12345 # Backend: False positive - код не используется
CVE-2024-67890 exp:2025-12-31 # Frontend: Патч выйдет в декабре
```

---

## 📚 Дополнительные ресурсы

### Официальная документация

- 📖 [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- 🐙 [GitHub Repository](https://github.com/aquasecurity/trivy)
- 💬 [Community Discussions](https://github.com/aquasecurity/trivy/discussions)

### Полезные ссылки

- [CVE Details](https://www.cvedetails.com/) - Информация о CVE
- [NVD Database](https://nvd.nist.gov/) - National Vulnerability Database
- [Docker Security](https://docs.docker.com/engine/security/) - Docker Security Best Practices

### Обновления

Следите за обновлениями:
- Trivy: `docker pull aquasec/trivy:latest`
- База данных: обновляется автоматически при каждом сканировании

---

## 🤝 Поддержка

### Вопросы и проблемы

1. Проверьте [Troubleshooting](#troubleshooting)
2. Просмотрите логи в `trivy/logs/`
3. Обратитесь к команде разработки

### Обратная связь

Если нашли проблему или есть предложение:
- Создайте issue в репозитории проекта
- Свяжитесь с security team

---

## 📝 Changelog

### 2025-10-08
- ✅ Инициализация Trivy сканирования
- ✅ Обновление nginx до 1.29.1-alpine (CVE-2025-23419)
- ✅ Создание PowerShell скриптов для сканирования
- ✅ Конфигурация для Backend, Frontend, Database

---

## 📄 Лицензия

Trivy is licensed under Apache License 2.0  
© 2023 Aqua Security Software Ltd.

---

**🛡️ Безопасность - это путь, а не место назначения. Сканируйте регулярно!**

