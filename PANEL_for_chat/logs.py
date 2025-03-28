import os
import logging
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOG_LEVEL, MAX_LOG_SIZE

# Настройка логгера
logger = logging.getLogger('app_logger')
logger.setLevel(getattr(logging, LOG_LEVEL))

# Создаем директорию для логов, если её нет
log_dir = os.path.dirname(LOG_FILE)
if log_dir:  # Проверяем, что путь не пустой
    os.makedirs(log_dir, exist_ok=True)

# Настройка ротации логов
handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=MAX_LOG_SIZE,
    encoding='utf-8'
)

# Форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def clear_logs():
    """Очистка файла логов"""
    try:
        # Удаляем все обработчики логгера
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()  # Закрываем обработчик

        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            logger.info("Логи успешно очищены.")
        else:
            logger.info("Файл логов не найден, ничего не очищаем.")
        
        # Настройка ротации логов заново
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.info("=== Логи приложения ===")
    except Exception as e:
        logger.error(f"Ошибка при очистке логов: {str(e)}")

def log_event(event_name: str, details: str = "", level: str = "INFO"):
    """
    Запись события в лог-файл
    """
    try:
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"{event_name}: {details}")
    except Exception as e:
        logger.error(f"Ошибка при записи лога: {str(e)}")