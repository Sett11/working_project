"""
Модуль кастомного логгера для проекта.

Содержит:
- Класс Logger с ротацией логов по времени (раз в сутки)
- Автоматическое создание директории для логов
- Унифицированный формат логирования
- Безопасная обработка ошибок при создании файловых обработчиков
"""
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import sys

def ensure_log_directory(log_file):
    """
    Проверяет наличие директории для логов и создаёт её, если она отсутствует.
    Это необходимо для корректной работы файлового логгера.
    Args:
        log_file (str): Путь к файлу лога (может содержать поддиректории).
    """
    log_dir = os.path.dirname(log_file)
    # Проверяем, существует ли директория для логов
    if not os.path.exists(log_dir):
        # Если директории нет — создаём её
        os.makedirs(log_dir, exist_ok=True)

def safe_log_error(message):
    """
    Безопасно логирует ошибку, используя print если логгер недоступен.
    
    Args:
        message (str): Сообщение об ошибке для логирования
    """
    try:
        print(f"LOGGER ERROR: {message}", file=sys.stderr)
    except Exception:
        # Если даже print не работает, игнорируем ошибку
        pass

class Logger(logging.Logger):
    """
    Кастомный логгер с ротацией логов по времени (раз в сутки).
    Используется для записи логов приложения в файл с автоматическим созданием новой версии каждый день.
    """
    def __init__(self, name, log_file, level=logging.INFO):
        """
        Инициализация класса Logger.

        :param name: Имя логгера (обычно имя файла, где используется логгер).
        :param log_file: Имя файла для сохранения логов (без папки logs, она добавляется автоматически).
        :param level: Уровень логгирования (по умолчанию INFO).
        """
        super().__init__(name, level)

        # Форматтер для логов: время, имя логгера, уровень, сообщение
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Безопасное создание обработчика с обработкой исключений
        handler = None
        log_path = None
        
        try:
            # Создаем путь к файлу лога и убеждаемся что директория logs существует
            log_path = str(Path("logs") / log_file)
            ensure_log_directory(log_path)
            
            # Попытка создать обработчик для ротации файлов по времени (раз в сутки)
            handler = TimedRotatingFileHandler(log_path, when="midnight", interval=1, encoding='utf-8')
            handler.suffix = "%Y-%m-%d"
            handler.setFormatter(formatter)
            
            # Добавление обработчика в логгер только при успешном создании
            self.addHandler(handler)
            
        except Exception as e:
            # Логируем ошибку безопасным способом
            error_msg = f"Не удалось создать файловый обработчик для {log_path or 'неизвестного пути'}: {str(e)}"
            safe_log_error(error_msg)
            
            # Очищаем частично созданный обработчик
            if handler is not None:
                try:
                    handler.close()
                except Exception:
                    pass
            
            # Fallback: создаем StreamHandler для вывода в консоль
            try:
                fallback_handler = logging.StreamHandler(sys.stdout)
                fallback_handler.setFormatter(formatter)
                self.addHandler(fallback_handler)
                safe_log_error(f"Используется fallback StreamHandler для логгера {name}")
            except Exception as fallback_error:
                # Если даже fallback не работает, создаем NullHandler
                try:
                    null_handler = logging.NullHandler()
                    self.addHandler(null_handler)
                    safe_log_error(f"Используется NullHandler для логгера {name} из-за ошибки: {str(fallback_error)}")
                except Exception:
                    # Если ничего не работает, просто игнорируем
                    safe_log_error(f"Не удалось создать никакой обработчик для логгера {name}")