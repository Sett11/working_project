"""
Модуль для настройки подключения к базе данных.

Этот файл отвечает за:
- Загрузку переменных окружения из .env файла.
- Определение URL для подключения к базе данных (с приоритетом для Docker).
- Создание движка (engine) SQLAlchemy для взаимодействия с БД.
- Создание фабрики сессий (SessionLocal) для управления подключениями.
- Определение базового класса для декларативных моделей (Base).
- Функцию-генератор `get_session` для использования в зависимостях FastAPI.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from utils.mylogger import Logger

# Инициализация логгера для событий, связанных с базой данных.
# log_file указывается без папки logs, чтобы использовать дефолтную директорию логов.
logger = Logger(name=__name__, log_file="db.log")

# Загружаем переменные окружения из файла .env.
# Это позволяет хранить конфигурацию отдельно от кода.
load_dotenv()
logger.info("Переменные окружения загружены.")

# Определяем URL для подключения к базе данных.
# Приоритет отдается переменной DATABASE_URL, которая обычно передается
# из docker-compose для работы в контейнере.
# Если она не найдена, используется DATABASE_URL_LOCAL для локального запуска.
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_LOCAL")

# Проверяем, что URL базы данных определен.
if not DATABASE_URL:
    logger.error("Переменные окружения для подключения к БД (DATABASE_URL или DATABASE_URL_LOCAL) не найдены.")
    raise ValueError("Необходимо определить DATABASE_URL или DATABASE_URL_LOCAL в .env файле")

logger.info(f"Используется URL базы данных: {DATABASE_URL.split('@')[-1]}") # Логируем без учетных данных

try:
    # Создаём движок SQLAlchemy, который будет управлять подключениями к БД.
    engine = create_engine(DATABASE_URL)
    
    # Создаём фабрику сессий. Каждая сессия будет представлять собой
    # отдельный диалог с базой данных.
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Создаём базовый класс для всех декларативных моделей SQLAlchemy.
    Base = declarative_base()
    
    logger.info("Соединение с базой данных успешно настроено.")
except Exception as e:
    logger.error(f"Ошибка при настройке соединения с базой данных: {e}", exc_info=True)
    # Если произошла ошибка, прерываем выполнение, так как без БД приложение неработоспособно.
    raise

def get_session():
    """
    Зависимость FastAPI для получения сессии базы данных.

    Эта функция-генератор создаёт новую сессию для каждого входящего запроса,
    передаёт ее в эндпоинт и гарантированно закрывает после завершения запроса.

    Yields:
        Session: Объект сессии SQLAlchemy.
    """
    db = SessionLocal()
    logger.debug(f"Сессия базы данных {id(db)} создана.")
    try:
        # Передаём управление эндпоинту.
        yield db
    finally:
        # Закрываем сессию после того, как эндпоинт отработал.
        db.close()
        logger.debug(f"Сессия базы данных {id(db)} закрыта.")
