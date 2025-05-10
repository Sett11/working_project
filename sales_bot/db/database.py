import aiosqlite
from datetime import datetime
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from utils.mylogger import Logger

load_dotenv()

MAX_REQUESTS_PER_DAY = int(os.environ.get("MAX_REQUESTS_PER_DAY", 3))
MAX_REQUESTS_PER_USER = int(os.environ.get("MAX_REQUESTS_PER_USER", 10))

logger = Logger("db", "database.log")

class Database:
    """Класс для асинхронной работы с SQLite базой данных"""
    def __init__(self, db_name="users.db"):
        self.db_name = str(Path("db") / db_name)
        self.connection = None
        # Создаем директорию для БД если её нет
        os.makedirs(os.path.dirname(self.db_name), exist_ok=True)
        logger.info(f"Инициализация базы данных {self.db_name}")

    async def connect(self):
        """Установка соединения с базой данных"""
        if not self.connection:
            self.connection = await aiosqlite.connect(self.db_name)
            await self._init_db()
            logger.info(f"Соединение с базой {self.db_name} установлено")
        return self.connection

    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info(f"Соединение с базой {self.db_name} закрыто")

    async def _init_db(self):
        """Инициализация таблиц в базе данных"""
        try:
            async with self.connection.cursor() as cursor:
                # Таблица пользователей
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP
                    )
                """)
                
                # Таблица запросов
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        request_type TEXT,
                        tokens_used INTEGER,
                        cost REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Таблица сессий
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        step INTEGER,
                        data TEXT,  -- JSON данные сессии
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        tokens_used INTEGER,
                        total_cost REAL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                await self.connection.commit()
                logger.info("Таблицы базы данных успешно инициализированы")
                
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
            raise

    async def log_request(self, user_id: int, request_type: str, tokens: int, cost: float):
        """Логирование запроса пользователя"""
        try:
            await self.connect()
            async with self.connection.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO requests (user_id, request_type, tokens_used, cost) VALUES (?, ?, ?, ?)",
                    (user_id, request_type, tokens, cost)
                )
                await self.connection.commit()
                logger.info(f"Запрос пользователя {user_id} залогирован: {request_type}")
                
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при логировании запроса: {str(e)}")
            raise
        finally:
            await self.close()

    async def check_rate_limit(self, user_id: int) -> tuple:
        """Проверка ограничений на запросы"""
        try:
            await self.connect()
            async with self.connection.cursor() as cursor:
                # Проверка дневного лимита
                await cursor.execute("""
                    SELECT COUNT(*) FROM requests 
                    WHERE user_id = ? AND created_at > datetime('now', '-1 day')
                """, (user_id,))
                daily_count = (await cursor.fetchone())[0]
                
                # Проверка общего лимита
                await cursor.execute("""
                    SELECT COUNT(*) FROM requests WHERE user_id = ?
                """, (user_id,))
                total_count = (await cursor.fetchone())[0]
                
                return daily_count < MAX_REQUESTS_PER_DAY, total_count < MAX_REQUESTS_PER_USER
                
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при проверке лимитов: {str(e)}")
            raise Exception("Ошибка при проверке лимитов. Пожалуйста, попробуйте позже.")
        finally:
            await self.close()

    async def save_session_data(self, user_id: int, step: int, data: dict, tokens_used: int, total_cost: float):
        """Сохранение данных сессии в базу"""
        try:
            await self.connect()
            async with self.connection.cursor() as cursor:
                await cursor.execute(
                    """INSERT INTO sessions 
                    (user_id, step, data, completed_at, tokens_used, total_cost) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, step, json.dumps(data), datetime.now().isoformat(), tokens_used, total_cost)
                )
                await self.connection.commit()
                logger.info(f"Данные сессии пользователя {user_id} сохранены в базу")
                
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при сохранении сессии: {str(e)}")
            raise
        finally:
            await self.close()

    async def register_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        """Регистрация нового пользователя"""
        try:
            await self.connect()
            async with self.connection.cursor() as cursor:
                await cursor.execute(
                    """INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, last_active) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (user_id, username, first_name, last_name, datetime.now().isoformat())
                )
                await self.connection.commit()
                logger.info(f"Пользователь {user_id} зарегистрирован/обновлен в базе")
                
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при регистрации пользователя {user_id}: {str(e)}")
            raise
        finally:
            await self.close()

    async def get_user_stats(self, user_id: int) -> dict:
        """Получение статистики пользователя"""
        try:
            await self.connect()
            async with self.connection.cursor() as cursor:
                # Общее количество запросов
                await cursor.execute("SELECT COUNT(*) FROM requests WHERE user_id = ?", (user_id,))
                total_requests = (await cursor.fetchone())[0]
                
                # Запросы за последние 24 часа
                await cursor.execute("""
                    SELECT COUNT(*) FROM requests 
                    WHERE user_id = ? AND created_at > datetime('now', '-1 day')
                """, (user_id,))
                daily_requests = (await cursor.fetchone())[0]
                
                # Общее количество токенов
                await cursor.execute("SELECT SUM(tokens_used) FROM requests WHERE user_id = ?", (user_id,))
                total_tokens = (await cursor.fetchone())[0] or 0
                
                return {
                    'total_requests': total_requests,
                    'daily_requests': daily_requests,
                    'remaining_daily': max(0, MAX_REQUESTS_PER_DAY - daily_requests),
                    'remaining_total': max(0, MAX_REQUESTS_PER_USER - total_requests),
                    'total_tokens': total_tokens
                }
                
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при получении статистики пользователя: {str(e)}")
            return {}
        finally:
            await self.close()