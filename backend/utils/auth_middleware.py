"""
Middleware для аутентификации пользователей.

Содержит:
- Проверка токенов аутентификации
- Добавление user_id в контекст запроса
- Обработка неавторизованных запросов
- Автоматическая установка user_id в контекст логгера
- Rate limiting для предотвращения DDoS атак
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from collections import defaultdict
import time
from db.database import AsyncSessionLocal
from db import crud
from utils.auth import extract_token_from_header
from utils.mylogger import Logger
from utils.user_context import set_user_id, reset_user_id

logger = Logger(name=__name__, log_file="auth.log")

# ИСПРАВЛЕНИЕ: Простой rate limiter для предотвращения DDoS атак
# Хранит историю запросов по IP адресам
_rate_limit_cache = defaultdict(list)
_rate_limit_window = 60  # Окно в 60 секунд
_rate_limit_max_requests = 30  # Максимум 30 запросов в минуту с одного IP


def check_rate_limit(ip: str) -> bool:
    """
    Проверка rate limit для IP адреса.
    
    Args:
        ip (str): IP адрес клиента
        
    Returns:
        bool: True если запрос разрешён, False если превышен лимит
    """
    current_time = time.time()
    requests = _rate_limit_cache[ip]
    
    # Удаляем старые запросы за пределами временного окна
    requests = [req_time for req_time in requests if current_time - req_time < _rate_limit_window]
    _rate_limit_cache[ip] = requests
    
    # Проверяем лимит
    if len(requests) >= _rate_limit_max_requests:
        return False
    
    # Добавляем текущий запрос
    requests.append(current_time)
    return True


def cleanup_rate_limit_cache():
    """
    Периодическая очистка кэша rate limiter от старых записей.
    Вызывается автоматически при каждой проверке.
    """
    current_time = time.time()
    # Удаляем IP адреса без активности более 5 минут
    inactive_ips = [
        ip for ip, requests in _rate_limit_cache.items()
        if not requests or (current_time - requests[-1] > 300)
    ]
    for ip in inactive_ips:
        del _rate_limit_cache[ip]


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
    logger.debug(f"[AUTH_DEBUG] Заголовок Authorization: {authorization[:20] + '...' if authorization else 'ОТСУТСТВУЕТ'}")
    
    token = extract_token_from_header(authorization)
    logger.debug(f"[AUTH_DEBUG] Извлечённый токен: {token[:10] + '...' if token else 'ОТСУТСТВУЕТ'}")
    
    if not token:
        logger.warning(f"[AUTH_DEBUG] Токен не найден в заголовках для пути {request.url.path}")
        return None
    
    # Получаем сессию БД напрямую
    async with AsyncSessionLocal() as db:
        try:
            # Ищем пользователя по токену
            user = await crud.get_user_by_token(db, token)
            logger.debug(f"[AUTH_DEBUG] Результат поиска по токену: {user.username if user else 'НЕ НАЙДЕН'}")
            
            # Проверяем, что пользователь существует И активен
            if user and user.is_active:
                logger.info(f"[AUTH_DEBUG] Пользователь успешно авторизован: {user.username} (ID: {user.id})")
                return {
                    "id": user.id,
                    "username": user.username,
                    "is_active": user.is_active
                }
            # Если пользователь неактивен или не найден - возвращаем None
            if user and not user.is_active:
                logger.warning(f"[AUTH_DEBUG] Пользователь {user.username} неактивен")
            else:
                logger.warning(f"[AUTH_DEBUG] Пользователь с токеном не найден в БД")
            return None
        except Exception as e:
            logger.error(f"[AUTH_DEBUG] Ошибка при получении пользователя: {e}")
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
    # ИСПРАВЛЕНИЕ: Получаем IP адрес клиента в самом начале для rate limiting
    client_ip = request.client.host if request.client else "unknown"
    
    # ИСПРАВЛЕНИЕ: Применяем rate limit ко ВСЕМ запросам (включая статические и авторизованные)
    # Это защищает от DDoS атак через любые эндпоинты
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit превышен для IP: {client_ip}, путь: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Слишком много запросов. Попробуйте позже."}
        )
    
    # Периодически очищаем кэш (каждый 100-й запрос)
    if len(_rate_limit_cache) > 100:
        cleanup_rate_limit_cache()
    
    # ИСПРАВЛЕНИЕ: Игнорируем статические файлы и служебные эндпоинты (без логирования)
    # Теперь после проверки rate limit - это предотвращает спам в логах, но защищает от атак
    ignored_paths = {
        '/favicon.ico', '/robots.txt', '/sitemap.xml', '/security.txt', 
        '/.well-known/security.txt', '/apple-touch-icon.png', '/apple-touch-icon-precomposed.png'
    }
    if request.url.path in ignored_paths:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Not found"}
        )
    
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
    
    # ИСПРАВЛЕНИЕ: Получаем пользователя ТОЛЬКО после прохождения rate limit проверки
    # Это защищает дорогостоящий DB lookup от перегрузки
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
        
        # ИСПРАВЛЕНИЕ: Логируем только важные эндпоинты для снижения нагрузки
        # Убрано избыточное логирование каждого авторизованного запроса
        important_paths = {
            '/api/auth/login', '/api/auth/register', '/api/auth/logout',
            '/api/recreate_pool', '/api/cleanup_pool'  # Административные действия
        }
        if request.url.path in important_paths:
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
