"""
Модуль для аутентификации и авторизации пользователей.

Содержит:
- Хеширование и проверка паролей
- Генерация и проверка токенов
- Проверка секретного ключа
- Утилиты для работы с аутентификацией
"""
import bcrypt
import secrets
import string
from datetime import datetime, timedelta
import os
from typing import Optional
from utils.mylogger import Logger

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv может быть не установлен

logger = Logger(name=__name__, log_file="auth.log")


def hash_password(password: str) -> str:
    """
    Хеширование пароля с использованием bcrypt.
    
    Args:
        password (str): Пароль в открытом виде
        
    Returns:
        str: Хешированный пароль
    """
    logger.info("Хеширование пароля")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Проверка пароля.
    
    Args:
        password (str): Пароль в открытом виде
        hashed_password (str): Хешированный пароль
        
    Returns:
        bool: True если пароль верный
    """
    logger.info("Проверка пароля")
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def generate_token() -> str:
    """
    Генерация простого токена для сессии.
    
    Returns:
        str: Сгенерированный токен
    """
    logger.info("Генерация токена")
    # Генерируем токен из 32 случайных символов
    alphabet = string.ascii_letters + string.digits
    token = ''.join(secrets.choice(alphabet) for _ in range(32))
    return token


def get_token_expiry(hours: int = 2) -> datetime:
    """
    Получение времени истечения токена.
    
    Args:
        hours (int): Количество часов жизни токена
        
    Returns:
        datetime: Время истечения токена
    """
    return datetime.now() + timedelta(hours=hours)


def verify_secret_key(provided_key: str) -> bool:
    """
    Проверка секретного ключа.
    
    Args:
        provided_key (str): Предоставленный секретный ключ
        
    Returns:
        bool: True если ключ верный
    """
    logger.info("Проверка секретного ключа")
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        logger.error("SECRET_KEY не найден в переменных окружения")
        return False
    
    is_valid = provided_key == secret_key
    logger.info(f"Проверка секретного ключа: {'успешно' if is_valid else 'неудачно'}")
    return is_valid


def is_token_expired(expires_at: datetime) -> bool:
    """
    Проверка истечения токена.
    
    Args:
        expires_at (datetime): Время истечения токена
        
    Returns:
        bool: True если токен истек
    """
    return datetime.now() > expires_at


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Извлечение токена из заголовка Authorization.
    
    Args:
        authorization (Optional[str]): Заголовок Authorization
        
    Returns:
        Optional[str]: Токен или None
    """
    if not authorization:
        return None
    
    if authorization.startswith('Bearer '):
        return authorization[7:]  # Убираем 'Bearer '
    
    return None
