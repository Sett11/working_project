from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from utils.mylogger import Logger

# Инициализация логгера для базы данных
logger = Logger(name=__name__, log_file="db.log")

load_dotenv()

# Приоритет отдается DATABASE_URL, который передается из docker-compose.
# Если его нет, используется DATABASE_URL_LOCAL для локальных скриптов.
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_LOCAL")

if not DATABASE_URL:
    logger.error("Переменные окружения для подключения к БД (DATABASE_URL или DATABASE_URL_LOCAL) не найдены.")
    raise ValueError("Необходимо определить DATABASE_URL или DATABASE_URL_LOCAL в .env файле")

logger.info("Попытка подключения к базе данных...")
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Соединение с базой данных успешно настроено.")
except Exception as e:
    logger.error(f"Ошибка при настройке соединения с базой данных: {e}", exc_info=True)
    raise

def get_session():
    """
    Создаёт и возвращает новую сессию базы данных.
    """
    db = SessionLocal()
    logger.debug("Сессия базы данных создана.")
    try:
        yield db
    finally:
        db.close()
        logger.debug("Сессия базы данных закрыта.")
