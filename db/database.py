"""
Модуль для настройки подключения к базе данных с интеграцией Graceful Degradation.

Этот файл отвечает за:
- Загрузку переменных окружения из .env файла.
- Определение URL для подключения к базе данных (с приоритетом для Docker).
- Создание движка (engine) SQLAlchemy для взаимодействия с БД.
- Создание фабрики сессий (SessionLocal) для управления подключениями.
- Определение базового класса для декларативных моделей (Base).
- Функцию-генератор `get_session` для использования в зависимостях FastAPI.
- Интеграцию с Circuit Breaker для предотвращения каскадных сбоев.
- Graceful Degradation при проблемах с БД.
- Мониторинг состояния БД с fallback механизмами.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import InterfaceError, OperationalError, DBAPIError
from sqlalchemy import text
import asyncpg
import asyncio
import os
import time
from dotenv import load_dotenv
from utils.mylogger import Logger
from utils.graceful_degradation import (
    db_circuit_breaker, 
    CircuitBreakerOpenError,
    graceful_manager,
    fallback_manager
)

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

# Проверяем, что используется асинхронный драйвер
detected_scheme = DATABASE_URL.split("://")[0] if "://" in DATABASE_URL else "unknown"
if not DATABASE_URL.startswith(("postgresql+asyncpg://", "postgres+asyncpg://")):
    logger.warning(
        f"⚠️ DATABASE_URL может использовать не асинхронный драйвер. "
        f"Обнаружена схема: '{detected_scheme}'. "
        f"Рекомендуется использовать 'postgresql+asyncpg://' или 'postgres+asyncpg://' для async engine."
    )

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
    
    Упрощённая версия без сложной логики восстановления для избежания
    проблем с generator athrow().

    Yields:
        AsyncSession: Объект асинхронной сессии SQLAlchemy.
        
    Raises:
        CircuitBreakerOpenError: Если Circuit Breaker открыт
        Exception: При критических ошибках БД
    """
    # Проверяем состояние Circuit Breaker
    cb_status = db_circuit_breaker.get_status()
    if cb_status["state"] == "open":
        logger.warning("🚨 Circuit Breaker открыт - блокируем запрос к БД")
        graceful_manager.enter_degradation_mode("Circuit Breaker открыт в get_session")
        raise CircuitBreakerOpenError("База данных недоступна (Circuit Breaker открыт)")
    
    # Создаём сессию и отдаём её
    async with AsyncSessionLocal() as session:
        session_id = id(session)
        logger.debug(f"Асинхронная сессия базы данных {session_id} создана.")
        
        try:
            # Проверяем соединение с БД через Circuit Breaker
            await db_circuit_breaker.acall(_test_db_connection, session)
            logger.debug(f"Соединение с БД проверено успешно для сессии {session_id}")
        except CircuitBreakerOpenError:
            logger.error(f"🚨 Circuit Breaker заблокировал сессию {session_id}")
            graceful_manager.enter_degradation_mode("Circuit Breaker заблокировал сессию")
            raise
        except Exception as test_error:
            logger.error(f"Ошибка проверки соединения {session_id}: {test_error}")
            graceful_manager.enter_degradation_mode(f"Ошибка проверки БД: {test_error}")
            raise
        
        # Отдаём сессию
        yield session
        
        logger.debug(f"Асинхронная сессия базы данных {session_id} закрыта.")

async def _test_db_connection(session: AsyncSession):
    """
    Тестирует соединение с базой данных.
    Используется Circuit Breaker для проверки доступности БД.
    
    Args:
        session: Сессия базы данных для тестирования
        
    Raises:
        Exception: Если соединение недоступно
    """
    try:
        await session.execute(text("SELECT 1"))
        logger.debug("✅ Соединение с БД успешно протестировано")
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования соединения с БД: {e}")
        raise

async def _recreate_connection_pool_with_retry():
    """
    Пересоздает пул соединений с ограниченной политикой повторных попыток.
    Использует экспоненциальную задержку между попытками.
    
    Returns:
        tuple: (new_engine, new_session_factory) - новый engine и фабрика сессий
        
    Raises:
        Exception: Если все попытки пересоздания исчерпаны
    """
    max_pool_recreation_attempts = 3
    attempt = 0
    
    while attempt < max_pool_recreation_attempts:
        attempt += 1
        logger.warning(f"🔄 Попытка пересоздания пула соединений {attempt}/{max_pool_recreation_attempts}")
        
        try:
            new_engine, new_session_factory = await _recreate_connection_pool()
            logger.info(f"✅ Пул соединений успешно пересоздан с попытки {attempt}")
            return new_engine, new_session_factory  # Возвращаем новые объекты
        except Exception as e:
            logger.error(f"❌ Попытка {attempt} пересоздания пула не удалась: {e}")
            
            if attempt >= max_pool_recreation_attempts:
                logger.error(f"❌ ИСЧЕРПАНЫ ВСЕ ПОПЫТКИ ПЕРЕСОЗДАНИЯ ПУЛА ({max_pool_recreation_attempts}). Критическая ошибка!")
                raise  # Прерываем выполнение при превышении максимального количества попыток
            
            # Экспоненциальная задержка перед следующей попыткой (оптимизирована для снижения нагрузки)
            delay = min(2 ** attempt, 15)  # Максимум 15 секунд (уменьшено с 30 для снижения нагрузки)
            logger.info(f"⏳ Ожидание {delay} секунд перед следующей попыткой пересоздания пула...")
            await asyncio.sleep(delay)

async def _recreate_connection_pool():
    """
    Пересоздает пул соединений при критических ошибках.
    
    Returns:
        tuple: (new_engine, new_session_factory) - новый engine и фабрика сессий
        
    Raises:
        Exception: При критических ошибках пересоздания пула
    """
    global engine, AsyncSessionLocal
    try:
        logger.warning("🔄 Пересоздание пула соединений...")
        
        # Закрываем старый engine с таймаутом
        if engine:
            try:
                await engine.dispose()
                logger.info("✅ Старый engine успешно закрыт")
            except Exception as dispose_error:
                logger.warning(f"⚠️ Ошибка при закрытии старого engine: {dispose_error}")
        
        # Небольшая пауза для стабилизации
        await asyncio.sleep(1)
        
        # Создаём новый асинхронный движок SQLAlchemy с улучшенными настройками
        new_engine = create_async_engine(
            DATABASE_URL, 
            echo=False, 
            future=True,
            # Улучшенные настройки пула соединений
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,  # Уменьшаем время рецикла до 30 минут
            pool_timeout=30,
            pool_reset_on_return='commit',  # Сбрасываем состояние при возврате
        )

        # Создаём новую асинхронную фабрику сессий
        new_session_factory = async_sessionmaker(
            new_engine, 
            expire_on_commit=False, 
            class_=AsyncSession,
            autoflush=False,
            autocommit=False
        )
        
        # Проверяем работоспособность нового пула
        try:
            async with new_session_factory() as test_session:
                await test_session.execute(text("SELECT 1"))
            logger.info("✅ Пул соединений успешно пересоздан и протестирован")
        except Exception as test_error:
            logger.error(f"❌ Ошибка тестирования нового пула: {test_error}")
            raise
        
        # Возвращаем новые объекты вместо мутации глобальных переменных
        return new_engine, new_session_factory
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при пересоздании пула соединений: {e}")
        raise

async def get_database_status():
    """
    Получает статус базы данных с интеграцией Graceful Degradation.
    
    Returns:
        dict: Статус БД с информацией о Circuit Breaker и Graceful Degradation
    """
    try:
        # Проверяем состояние Circuit Breaker
        cb_status = db_circuit_breaker.get_status()
        
        # Проверяем состояние Graceful Degradation
        gd_status = graceful_manager.get_degradation_status()
        
        # Пытаемся получить статистику пула соединений
        pool_stats = {}
        try:
            pool = engine.pool
            pool_stats = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "utilization_percent": (pool.checkedout() / pool.size() * 100) if pool.size() > 0 else 0
            }
        except Exception as pool_error:
            logger.warning(f"Не удалось получить статистику пула: {pool_error}")
            pool_stats = {"error": str(pool_error)}
        
        # Определяем общий статус БД
        if cb_status["state"] == "open":
            db_status = "degraded"
        elif cb_status["state"] == "half_open":
            db_status = "recovering"
        else:
            db_status = "healthy"
        
        return {
            "database_status": db_status,
            "circuit_breaker": cb_status,
            "graceful_degradation": gd_status,
            "pool_stats": pool_stats,
            "connection_url": DATABASE_URL.split('@')[-1] if DATABASE_URL else None,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса БД: {e}")
        return {
            "database_status": "error",
            "error": str(e),
            "circuit_breaker": db_circuit_breaker.get_status(),
            "graceful_degradation": graceful_manager.get_degradation_status(),
            "pool_stats": {},
            "timestamp": time.time()
        }