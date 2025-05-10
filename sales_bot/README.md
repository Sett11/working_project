# Sales Assistant Bot 🤖

Чат-бот для подготовки к B2B-встречам с искусственным интеллектом. Автоматизирует создание:
- Гипотезы о закупочном центре компании
- Аватара ключевой роли
- Трёхуровневой модели продукта
- Ценностных связок
- Аргументации по технологии ТАП

## 🔍 Функционал
1. **7 этапов анализа**:
   - Сбор данных о компании-клиенте
   - Описание продукта/услуги
   - Формирование закупочного центра
   - Создание аватара ключевой роли
   - Построение трёхуровневой модели продукта
   - Генерация ценностных связок
   - Формирование аргументации (ТАП)

2. **Особенности**:
   - Работа с GPT-4.1-mini
   - Ограничение запросов на пользователя (дневной лимит и абсолютный)
   - Логирование всех операций
   - Экспорт результатов в файл
   - Статистика использования
   - Асинхронная обработка запросов
   - Сохранение данных в SQLite
   - Docker-контейнеризация

## 📋 Требования

- Python 3.10+
- Docker и Docker Compose (для запуска в контейнере)
- Telegram Bot Token
- OpenAI API ключ

## 🚀 Быстрый старт

### 1. Локальный запуск

1. Клонируйте репозиторий:
```bash
git clone <repository_url>
cd sales_bot_06052025
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/macOS
venv\Scripts\activate     # для Windows
pip install -r requirements.txt
```

3. Создайте файл `.env` в корневой директории проекта:
```env
TELEGRAM_TOKEN=ваш_токен_бота
OPENAI_API_KEY=ваш_ключ_openai
MAX_REQUESTS_PER_DAY=3
MAX_REQUESTS_PER_USER=10
MESSAGE_CHUNK_SIZE=4096
GPT_MODEL=gpt-4.1-mini
BASE_URL=url_api_используемой_модели
```

4. Запустите бота:
```bash
python bot.py
```

### 2. Запуск через Docker

1. Убедитесь, что Docker и Docker Compose установлены:
```bash
docker --version
docker-compose --version
```

2. Создайте файл `.env` как описано выше

3. Соберите и запустите контейнер:
```bash
docker-compose up --build -d
```

4. Проверьте логи:
```bash
docker-compose logs -f
```

### 3. Деплой на сервер

1. Подготовьте файлы для загрузки на сервер:
   - Убедитесь, что все файлы проекта присутствуют
   - Проверьте наличие и корректность `.env` файла
   - Проверьте, что `.gitignore` и `.dockerignore` настроены правильно

2. Загрузите файлы на сервер через WinSCP:
   - Подключитесь к серверу через WinSCP
   - Загрузите директорию `sales_bot_06052025` на сервер
   - Убедитесь, что все файлы успешно загружены

3. Подключитесь к серверу через PuTTY:
```bash
cd путь/к/sales_bot_06052025
docker-compose up --build -d
```

4. Проверьте статус:
```bash
docker-compose ps
docker-compose logs -f
```

## 📁 Структура проекта

```
sales_bot_06052025/
├── bot.py              # Основной файл бота
├── requirements.txt    # Зависимости проекта
├── Dockerfile         # Конфигурация Docker
├── docker-compose.yml # Конфигурация Docker Compose
├── .env              # Переменные окружения
├── README.md         # Документация
├── db/               # Модули работы с базой данных
├── utils/            # Вспомогательные модули
├── steps/            # Файлы с промптами для каждого шага
├── logs/             # Директория для логов
└── user_data/        # Директория для файлов пользователей
```

## 🔧 Обслуживание

### Просмотр логов
```bash
# Для Docker
docker-compose logs -f

# Локально
cat logs/bot_events.log
```

### Перезапуск бота
```bash
# Для Docker
docker-compose restart

# Локально
python bot.py
```

### Обновление
```bash
# Для Docker
git pull
docker-compose up --build -d

# Локально
git pull
pip install -r requirements.txt
python bot.py
```

## 📝 Лицензия

MIT License

## 👥 Поддержка

По всем вопросам обращайтесь:
- Telegram: @your_support
- Email: support@example.com

