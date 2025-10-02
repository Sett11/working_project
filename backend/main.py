"""
Основной файл для запуска backend-приложения (FastAPI).

Этот скрипт служит точкой входа для всего backend приложения.
"""
import uvicorn
import os
from dotenv import load_dotenv
from utils.mylogger import Logger

# Загружаем переменные окружения
load_dotenv()

# Инициализируем логгер
logger = Logger(name=__name__, log_file="backend.log")

# Настройки сервера
SERVER_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("BACKEND_PORT", "8000"))

if __name__ == "__main__":
    # Логируем попытку запуска с параметрами
    logger.info(
        f"Запуск FastAPI backend сервера на {SERVER_HOST}:{SERVER_PORT}...",
        extra={"user_id": "root_app"}
    )
    
    try:
        # uvicorn.run() - блокирующий вызов, который держит процесс
        # до получения сигнала прерывания (Ctrl+C) или критической ошибки
        uvicorn.run(
            "api.main:app",
            host=SERVER_HOST,
            port=SERVER_PORT,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        # Корректное завершение по Ctrl+C
        logger.info(
            "Backend сервер получил сигнал остановки (KeyboardInterrupt).",
            extra={"user_id": "root_app"}
        )
    except Exception as e:
        # Ошибки при запуске или во время работы
        logger.error(
            f"Критическая ошибка backend сервера: {e}",
            exc_info=True,
            extra={"user_id": "root_app"}
        )
        raise  # Пробрасываем исключение для видимости проблемы
    finally:
        # Выполняется при любом завершении
        logger.info(
            "Backend сервер остановлен.",
            extra={"user_id": "root_app"}
        )
