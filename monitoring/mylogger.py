"""
Автономный модуль логгера для мониторинга.
"""
import logging
import os
from datetime import datetime

class Logger:
    """Простой логгер для мониторинга"""
    
    def __init__(self, name: str, log_file: str = None):
        self.name = name
        self.logger = logging.getLogger(name)
        
        # Настраиваем форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Настраиваем обработчик для консоли
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Настраиваем обработчик для файла, если указан
        if log_file:
            # Создаем папку logs, если её нет
            # В Docker контейнере директория logs монтируется в /app/logs
            # Вне Docker создаем директорию logs в текущей директории
            logs_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(os.path.join(logs_dir, log_file))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Устанавливаем уровень логирования
        self.logger.setLevel(logging.INFO)
    
    def debug(self, message, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        self.logger.critical(message, *args, **kwargs)

# Re-export для обратной совместимости
__all__ = ['Logger']