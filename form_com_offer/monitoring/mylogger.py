"""
Модуль логгера для мониторинга.

Импортирует Logger из utils.mylogger для устранения дублирования кода.
"""
import sys
import os

# Добавляем путь к utils в sys.path для импорта
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from mylogger import Logger

# Re-export для обратной совместимости
__all__ = ['Logger']