"""
Middleware для аутентификации пользователей.

Содержит:
- Проверка токенов аутентификации
- Добавление user_id в контекст запроса
- Обработка неавторизованных запросов
- Автоматическая установка user_id в контекст логгера
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from db.database import AsyncSessionLocal
from db import crud
from utils.auth import extract_token_from_header
from utils.mylogger import Logger
from utils.user_context import set_user_id, reset_user_id

logger = Logger(name=__name__, log_file="auth.log")


async def get_current_user(request: Request) -> Optional[dict]:
    """
    Получение текущего пользователя из токена.
    
    Args:
        request (Request): FastAPI request объект
        
    Returns:
        Optional[dict]: Данные пользователя или None
    """
    # Извлекаем токен из заголовка
    authorization = request.headers.get('Authorization')
    token = extract_token_from_header(authorization)
    
    if not token:
        return None
    
    # Получаем сессию БД напрямую
    async with AsyncSessionLocal() as db:
        try:
            # Ищем пользователя по токену
            user = await crud.get_user_by_token(db, token)
            # Проверяем, что пользователь существует И активен
            if user and user.is_active:
                return {
                    "id": user.id,
                    "username": user.username,
                    "is_active": user.is_active
                }
            # Если пользователь неактивен или не найден - возвращаем None
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None


async def auth_middleware(request: Request, call_next):
    """
    Middleware для проверки аутентификации.
    
    Args:
        request (Request): FastAPI request объект
        call_next: Следующий обработчик
        
    Returns:
        Response: Ответ от следующего обработчика
    """
    # Исключаем эндпоинты аутентификации из проверки (точное совпадение)
    auth_paths = {'/api/auth/register', '/api/auth/login', '/docs', '/openapi.json', '/health'}
    if request.url.path in auth_paths:
        # Сохраняем текущий контекст и устанавливаем user_id=system для неавторизованных запросов
        context_token = set_user_id("system")
        try:
            response = await call_next(request)
            return response
        finally:
            # Восстанавливаем предыдущий контекст
            reset_user_id(context_token)
    
    # Делаем публичными эндпоинты мониторинга (проверка префикса с границей)
    monitoring_prefixes = ['/api/monitoring/', '/api/graceful-degradation/']
    if any(request.url.path.startswith(prefix) or request.url.path == prefix.rstrip('/') for prefix in monitoring_prefixes):
        context_token = set_user_id("system")
        try:
            response = await call_next(request)
            return response
        finally:
            reset_user_id(context_token)
    
    # Получаем пользователя
    user = await get_current_user(request)
    
    if not user:
        # Сохраняем текущий контекст и устанавливаем user_id=system для неавторизованных запросов
        context_token = set_user_id("system")
        try:
            logger.warning(f"Неавторизованный доступ к {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Требуется аутентификация"}
            )
        finally:
            # Восстанавливаем предыдущий контекст
            reset_user_id(context_token)
    
    # Устанавливаем user_id в контекст логгера
    context_token = set_user_id(user["username"])
    
    try:
        # Добавляем user_id в состояние запроса
        request.state.user_id = user["id"]
        request.state.username = user["username"]
        
        logger.info(f"Авторизованный доступ: user_id={user['id']}, username={user['username']}, path={request.url.path}")
        
        response = await call_next(request)
        return response
    finally:
        # Всегда очищаем контекст пользователя после обработки запроса
        reset_user_id(context_token)


def get_user_id_from_request(request: Request) -> Optional[int]:
    """
    Получение user_id из состояния запроса.
    
    Args:
        request (Request): FastAPI request объект
        
    Returns:
        Optional[int]: ID пользователя или None
    """
    return getattr(request.state, 'user_id', None)


def get_username_from_request(request: Request) -> Optional[str]:
    """
    Получение username из состояния запроса.
    
    Args:
        request (Request): FastAPI request объект
        
    Returns:
        Optional[str]: Username пользователя или None
    """
    return getattr(request.state, 'username', None)
