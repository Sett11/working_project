"""
Утилиты для управления контекстом пользователя в логах.

Содержит функции для установки и получения user_id в асинхронном контексте.
Используется для автоматического добавления user_id в логи FastAPI endpoints.
"""

from contextvars import ContextVar

# Глобальная переменная для хранения user_id в асинхронном контексте
user_id_var = ContextVar('user_id', default='system')

def set_user_id(user_id: str):
    """
    Устанавливает user_id в текущем асинхронном контексте.
    
    Args:
        user_id (str): Username пользователя или 'system'
        
    Returns:
        Token: Токен контекста для возможности сброса
    """
    return user_id_var.set(user_id)

def get_user_id() -> str:
    """
    Получает user_id из текущего асинхронного контекста.
    
    Returns:
        str: Username пользователя или 'system'
    """
    return user_id_var.get()

def clear_user_id():
    """
    Очищает user_id в текущем асинхронном контексте (устанавливает 'system').
    
    Returns:
        Token: Токен контекста для возможности сброса
    """
    return user_id_var.set('system')

def reset_user_id(token):
    """
    Сбрасывает user_id к предыдущему значению.
    
    Args:
        token: Токен контекста, полученный от set_user_id или clear_user_id
    """
    user_id_var.reset(token)
