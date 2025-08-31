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
from utils.user_context import set_user_id

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
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "is_active": user.is_active
                }
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
    # Исключаем эндпоинты аутентификации из проверки
    auth_paths = ['/api/auth/register', '/api/auth/login', '/docs', '/openapi.json', '/health']
    if any(request.url.path.startswith(path) for path in auth_paths):
        # Устанавливаем user_id=system для неавторизованных запросов
        set_user_id("system")
        response = await call_next(request)
        return response
    
    # Получаем пользователя
    user = await get_current_user(request)
    
    if not user:
        # Устанавливаем user_id=system для неавторизованных запросов
        set_user_id("system")
        logger.warning(f"Неавторизованный доступ к {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Требуется аутентификация"}
        )
    
    # Устанавливаем user_id в контекст логгера
    set_user_id(user["username"])
    
    # Добавляем user_id в состояние запроса
    request.state.user_id = user["id"]
    request.state.username = user["username"]
    
    logger.info(f"Авторизованный доступ: user_id={user['id']}, username={user['username']}, path={request.url.path}")
    
    response = await call_next(request)
    return response


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
