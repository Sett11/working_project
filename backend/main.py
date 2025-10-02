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
    logger.info("Запуск FastAPI backend сервера...")
    
    try:
        uvicorn.run(
            "api.main:app",
            host=SERVER_HOST,
            port=SERVER_PORT,
            reload=True,
            log_level="info"
        )
        logger.info("Backend сервер успешно запущен.")
    except Exception as e:
        logger.error(f"Ошибка при запуске backend сервера: {e}", exc_info=True)
    finally:
        logger.info("Backend сервер остановлен.")
