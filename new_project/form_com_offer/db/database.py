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
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
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
    # Создаём асинхронный движок SQLAlchemy для работы с asyncpg
    # Настраиваем пул соединений для предотвращения утечек
    engine = create_async_engine(
        DATABASE_URL, 
        echo=False, 
        future=True,
        # Настройки пула соединений
        pool_size=10,  # Максимальное количество соединений в пуле
        max_overflow=20,  # Дополнительные соединения при переполнении
        pool_pre_ping=True,  # Проверка соединений перед использованием
        pool_recycle=3600,  # Пересоздание соединений каждый час
        pool_timeout=30,  # Таймаут ожидания свободного соединения
        # Настройки для asyncpg
        poolclass=None,  # Используем дефолтный пул для async
    )

    # Создаём асинхронную фабрику сессий
    AsyncSessionLocal = async_sessionmaker(
        engine, 
        expire_on_commit=False, 
        class_=AsyncSession,
        autoflush=False,  # Отключаем автоматический flush
        autocommit=False  # Отключаем автоматический commit
    )

    # Создаём базовый класс для всех декларативных моделей SQLAlchemy (общий для sync/async)
    Base = declarative_base()

    logger.info("Асинхронное соединение с базой данных успешно настроено.")
except Exception as e:
    logger.error(f"Ошибка при настройке соединения с базой данных: {e}", exc_info=True)
    # Если произошла ошибка, прерываем выполнение, так как без БД приложение неработоспособно.
    raise

async def get_session():
    """
    Асинхронная зависимость FastAPI для получения сессии базы данных.

    Эта функция-генератор создаёт новую асинхронную сессию для каждого входящего запроса,
    передаёт ее в эндпоинт и гарантированно закрывает после завершения запроса.

    Yields:
        AsyncSession: Объект асинхронной сессии SQLAlchemy.
    """
    async with AsyncSessionLocal() as session:
        session_id = id(session)
        logger.debug(f"Асинхронная сессия базы данных {session_id} создана.")
        try:
            yield session
        except Exception as e:
            logger.error(f"Ошибка в сессии {session_id}: {e}")
            raise
        finally:
            logger.debug(f"Асинхронная сессия базы данных {session_id} закрыта.")
            # Логируем статистику пула соединений
            pool = engine.pool
            logger.debug(f"Статистика пула: размер={pool.size()}, проверено={pool.checkedin()}, в использовании={pool.checkedout()}")