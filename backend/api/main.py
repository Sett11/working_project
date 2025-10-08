"""
Минимальный файл бэкенда с только необходимыми эндпоинтами.
Включает аутентификацию, мониторинг и основные функции.
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH для доступа к модулю db
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import datetime
import re
from db import crud, schemas
from db.database import get_session, AsyncSessionLocal, engine
from utils.mylogger import Logger
from utils.graceful_degradation import graceful_fallback, graceful_manager
from db.schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from utils.auth import hash_password, verify_password, generate_token, get_token_expiry, verify_secret_key
from utils.auth_middleware import auth_middleware, get_user_id_from_request, get_username_from_request
import json
import time
import asyncio
import os

logger = Logger(name=__name__, log_file="backend.log")
app = FastAPI(title="Air-Con Commercial Offer API", version="0.1.0")

# Добавляем middleware для аутентификации
app.middleware("http")(auth_middleware)

# Вспомогательная функция для проверки прав администратора
async def verify_admin(request: Request, db: AsyncSession) -> int:
    """
    Проверка аутентификации и прав администратора.
    
    Args:
        request: FastAPI Request объект
        db: Сессия базы данных
        
    Returns:
        int: ID пользователя-администратора
        
    Raises:
        HTTPException: 401 если не аутентифицирован, 403 если не администратор
    """
    user_id = get_user_id_from_request(request)
    if not user_id:
        logger.warning(f"Попытка доступа к админ-эндпоинту без аутентификации")
        raise HTTPException(status_code=401, detail="Требуется аутентификация")
    
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        logger.warning(f"Пользователь user_id={user_id} не найден при проверке прав администратора")
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    
    if not user.is_admin:
        logger.warning(f"Пользователь user_id={user_id} ({user.username}) попытался получить доступ к админ-эндпоинту без прав")
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    
    logger.info(f"Администратор user_id={user_id} ({user.username}) получил доступ к админ-эндпоинту")
    return user_id

# Глобальный обработчик исключений
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Необработанное исключение: {exc}", exc_info=True)
    return JSONResponse(
        content={"error": "Внутренняя ошибка сервера", "detail": str(exc)},
        status_code=500
    )

# === СОБЫТИЯ ЖИЗНЕННОГО ЦИКЛА ===

@app.on_event("startup")
async def startup_event():
    logger.info("Запуск FastAPI приложения...")
    
    # Запускаем автоматический мониторинг
    try:
        from utils.monitoring import monitor
        await monitor.start_monitoring()
        logger.info("✅ Автоматический мониторинг приложения запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска автоматического мониторинга: {e}")
    
    # Запускаем Circuit Breaker мониторинг
    try:
        from utils.graceful_degradation import db_circuit_breaker
        await db_circuit_breaker.start_monitoring()
        logger.info("✅ Circuit Breaker мониторинг запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска Circuit Breaker мониторинга: {e}")
    
    # Запускаем Graceful Degradation Manager
    try:
        from utils.graceful_degradation import graceful_manager
        logger.info("✅ Graceful Degradation Manager инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации Graceful Degradation Manager: {e}")
    
    # Запускаем Fallback Manager
    try:
        from utils.graceful_degradation import fallback_manager
        fallback_manager.start()
        logger.info("✅ Fallback Manager запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска Fallback Manager: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Остановка FastAPI приложения...")
    
    # Останавливаем Fallback Manager
    try:
        from utils.graceful_degradation import fallback_manager
        fallback_manager.stop()
        logger.info("✅ Fallback Manager остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка остановки Fallback Manager: {e}")
    
    # Останавливаем Circuit Breaker мониторинг
    try:
        from utils.graceful_degradation import db_circuit_breaker
        await db_circuit_breaker.stop_monitoring()
        logger.info("✅ Circuit Breaker мониторинг остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка остановки Circuit Breaker мониторинга: {e}")
    
    # Останавливаем Graceful Degradation Manager
    try:
        from utils.graceful_degradation import graceful_manager
        if graceful_manager.is_in_degradation_mode():
            graceful_manager.exit_degradation_mode()
        logger.info("✅ Graceful Degradation Manager остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка остановки Graceful Degradation Manager: {e}")

# === СИСТЕМНЫЕ ЭНДПОИНТЫ ===

@app.get("/health")
@graceful_fallback("health_check", cache_key="health_status", cache_ttl=60)
async def health_check():
    """Эндпоинт для проверки здоровья приложения"""
    try:
        from db.database import AsyncSessionLocal, engine
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        
        # Получаем статистику пула соединений
        pool = engine.pool
        pool_stats = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
            # Метод invalid() не существует для AsyncAdaptedQueuePool
        }
        
        return {
            "status": "healthy", 
            "database": "connected",
            "pool_stats": pool_stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)},
            status_code=503
        )

# === АУТЕНТИФИКАЦИЯ ===

@app.post("/api/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_session)):
    """Регистрация нового пользователя"""
    try:
        # Проверяем, существует ли пользователь
        existing_user = await crud.get_user_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует")
        
        # Хешируем пароль
        hashed_password = hash_password(user_data.password)
        
        # Создаем пользователя
        user = await crud.create_user(db, user_data, hashed_password)
        
        # Генерируем токен
        expiry_time = get_token_expiry()
        token_data = {
            "user_id": user.id,
            "username": user.username,
            "exp": expiry_time
        }
        token = generate_token(token_data)
        
        logger.info(f"Пользователь {user.username} успешно зарегистрирован")
        
        # Формируем ответ в формате, который ожидает frontend
        return TokenResponse(
            token=token,
            expires_at=expiry_time.isoformat(),  # Конвертируем datetime в ISO string
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.post("/api/auth/login", response_model=TokenResponse)
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_session)):
    """Аутентификация пользователя"""
    try:
        # Получаем пользователя по имени
        user = await crud.get_user_by_username(db, user_data.username)
        if not user:
            raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
        
        # Проверяем пароль
        if not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
        
        # Проверяем, активен ли пользователь
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Аккаунт деактивирован")
        
        # Генерируем токен
        expiry_time = get_token_expiry()
        token_data = {
            "user_id": user.id,
            "username": user.username,
            "exp": expiry_time
        }
        token = generate_token(token_data)
        
        logger.info(f"Пользователь {user.username} успешно аутентифицирован")
        
        # Формируем ответ в формате, который ожидает frontend
        return TokenResponse(
            token=token,
            expires_at=expiry_time.isoformat(),  # Конвертируем datetime в ISO string
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при аутентификации пользователя: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user(request: Request, db: AsyncSession = Depends(get_session)):
    """Получение информации о текущем пользователе"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        user = await crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.delete("/api/auth/delete")
async def delete_account(request: Request, db: AsyncSession = Depends(get_session)):
    """Удаление аккаунта текущего пользователя"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        # Проверяем, существует ли пользователь
        user = await crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Удаляем пользователя
        deleted = await crud.delete_user(db, user_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Не удалось удалить аккаунт")
        
        logger.info(f"Пользователь {user.username} (id={user_id}) успешно удалил свой аккаунт")
        return {"message": "Аккаунт успешно удален"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении аккаунта: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

# === МОНИТОРИНГ ===

@app.get("/api/monitoring/status")
@graceful_fallback("monitoring_status", cache_key="monitoring_status", cache_ttl=60)
async def get_monitoring_status():
    """Расширенный эндпоинт для мониторинга состояния приложения с интеграцией Graceful Degradation"""
    try:
        # Используем автоматический монитор
        from utils.monitoring import monitor
        health_status = await monitor.get_health_status()
        
        # Добавляем информацию о состоянии БД с graceful degradation
        from db.database import get_database_status
        db_status = await get_database_status()
        
        # Обогащаем ответ информацией о graceful degradation
        health_status["database_graceful_status"] = db_status
        
        # Добавляем информацию о graceful degradation из менеджера
        if graceful_manager.is_in_degradation_mode():
            health_status["graceful_degradation_warning"] = "Приложение работает в режиме graceful degradation"
        
        return health_status
    except Exception as e:
        logger.error(f"Monitoring status check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/api/graceful-degradation/status")
async def get_graceful_degradation_status():
    """Эндпоинт для мониторинга состояния graceful degradation"""
    try:
        return graceful_manager.get_degradation_status()
    except Exception as e:
        logger.error(f"Graceful degradation status check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/api/database/status")
@graceful_fallback("database_status", cache_key="db_status", cache_ttl=30)
async def get_database_status_endpoint():
    """Эндпоинт для получения детального статуса базы данных с Graceful Degradation"""
    try:
        from db.database import get_database_status
        return await get_database_status()
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return {
            "database_status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/api/graceful-degradation/recovery")
async def attempt_graceful_recovery():
    """Эндпоинт для принудительной попытки восстановления"""
    try:
        success = await graceful_manager.attempt_recovery()
        return {
            "success": success,
            "message": "Попытка восстановления выполнена" if success else "Восстановление не удалось",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Graceful recovery attempt failed: {e}")
        return {"success": False, "error": str(e), "timestamp": time.time()}

@app.post("/api/recreate_pool")
async def recreate_connection_pool(request: Request, db: AsyncSession = Depends(get_session)):
    """Эндпоинт для пересоздания пула соединений (только для администраторов)"""
    # Проверяем права администратора
    user_id = await verify_admin(request, db)
    
    try:
        from db.database import _recreate_connection_pool
        logger.info(f"Администратор user_id={user_id} инициировал пересоздание пула соединений")
        await _recreate_connection_pool()
        logger.info(f"Пул соединений успешно пересоздан администратором user_id={user_id}")
        return {"status": "success", "message": "Пул соединений пересоздан"}
    except Exception as e:
        logger.error(f"Ошибка при пересоздании пула администратором user_id={user_id}: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/cleanup_pool")
async def cleanup_connection_pool(request: Request, db: AsyncSession = Depends(get_session)):
    """Эндпоинт для graceful очистки пула соединений (только для администраторов)"""
    # Проверяем права администратора
    user_id = await verify_admin(request, db)
    
    try:
        from db.database import engine
        pool = engine.pool
        
        # Получаем настраиваемый таймаут из переменной окружения (по умолчанию 5 секунд)
        drain_timeout = int(os.getenv("POOL_DRAIN_TIMEOUT", "5"))
        check_interval = 0.5  # Проверяем каждые 0.5 секунды
        
        # Получаем статистику до очистки
        before_stats = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
        
        logger.info(f"Администратор user_id={user_id} начинает graceful очистку пула. Текущее состояние: {before_stats}")
        
        # Graceful shutdown: закрываем пул для новых соединений
        await engine.dispose()
        
        # Активное ожидание завершения соединений
        elapsed_time = 0
        while elapsed_time < drain_timeout:
            checked_out = pool.checkedout()
            
            if checked_out == 0:
                logger.info(f"Все соединения закрыты за {elapsed_time:.1f} сек")
                break
            
            logger.info(f"Ожидание закрытия соединений: {checked_out} активных, прошло {elapsed_time:.1f}/{drain_timeout} сек")
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
        
        # Получаем статистику после очистки
        after_stats = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
        
        # Проверяем, истек ли таймаут
        if after_stats["checked_out"] > 0:
            logger.warning(
                f"Graceful очистка пула завершена с таймаутом. "
                f"Осталось активных соединений: {after_stats['checked_out']}. "
                f"Администратор user_id={user_id}"
            )
            return {
                "status": "warning",
                "message": f"Таймаут истек, осталось {after_stats['checked_out']} активных соединений",
                "before_stats": before_stats,
                "after_stats": after_stats,
                "elapsed_time": elapsed_time,
                "timeout": drain_timeout,
                "timestamp": time.time()
            }
        
        logger.info(f"Graceful очистка пула успешно завершена администратором user_id={user_id}. Состояние после: {after_stats}")
        
        return {
            "status": "success", 
            "message": "Пул соединений очищен gracefully",
            "before_stats": before_stats,
            "after_stats": after_stats,
            "elapsed_time": elapsed_time,
            "timeout": drain_timeout,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Ошибка при graceful очистке пула администратором user_id={user_id}: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/monitoring/start")
async def start_monitoring():
    """Эндпоинт для запуска автоматического мониторинга"""
    try:
        from utils.monitoring import monitor
        await monitor.start_monitoring()
        return {"status": "success", "message": "Автоматический мониторинг запущен"}
    except Exception as e:
        logger.error(f"Ошибка запуска мониторинга: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/monitoring/stop")
async def stop_monitoring():
    """Эндпоинт для остановки автоматического мониторинга"""
    try:
        from utils.monitoring import monitor
        await monitor.stop_monitoring()
        return {"status": "success", "message": "Автоматический мониторинг остановлен"}
    except Exception as e:
        logger.error(f"Ошибка остановки мониторинга: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/monitoring/control")
async def get_monitoring_control():
    """Эндпоинт для получения статуса автоматического мониторинга"""
    try:
        from utils.monitoring import monitor
        return {
            "monitoring_active": monitor.monitoring_active,
            "alert_cooldown": monitor.alert_cooldown,
            "last_alerts_count": len(monitor.last_alert_time)
        }
    except Exception as e:
        logger.error(f"Ошибка получения статуса мониторинга: {e}")
        return {"status": "error", "message": str(e)}

# === ОСНОВНЫЕ ЭНДПОИНТЫ ===

@app.post("/api/select_aircons/")
async def select_aircons_endpoint(request: Request, payload: dict, db: AsyncSession = Depends(get_session)):
    """Подбор кондиционеров по параметрам"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        aircon_params = payload.get("aircon_params", {})
        
        from utils.compose_aircon_selector import select_aircons_for_params
        selected_aircons = await select_aircons_for_params(db, aircon_params)
        
        total_count = len(selected_aircons)
        logger.info(f"Подбор кондиционеров: найдено {total_count} вариантов")
        
        response_data = {
            "total_count": total_count,
            "aircons_list": selected_aircons
        }
        
        return response_data
    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при подборе кондиционеров: {e}")


@app.get("/api/all_orders/")
@graceful_fallback("orders_list", cache_key="all_orders_list", cache_ttl=300)
async def get_all_orders_list(request: Request, db: AsyncSession = Depends(get_session)):
    """Получение объединенного списка всех заказов"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        # Получаем составные заказы
        compose_orders = await crud.get_compose_orders_by_user_id(db, user_id)
        
        all_orders = []
        
        # Добавляем составные заказы
        for order in compose_orders:
            client_data = order.compose_order_data.get("client_data", {})
            all_orders.append({
                "id": order.id,
                "client_name": client_data.get("full_name", "Неизвестно"),
                "address": client_data.get("address", "Адрес не указан"),
                "created_at": order.created_at.strftime('%Y-%m-%d'),
                "status": order.status,
                "order_type": "Compose"
            })
        
        # Сортируем по дате создания (новые выше)
        all_orders.sort(key=lambda x: x["created_at"], reverse=True)
        
        logger.info(f"Отправлен объединенный список заказов: {len(all_orders)} заказов")
        
        return all_orders
    except Exception as e:
        logger.error(f"Ошибка при получении объединенного списка заказов: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка заказов: {str(e)}")

@app.get("/api/compose_order/{order_id}")
async def get_compose_order_by_id(request: Request, order_id: int, db: AsyncSession = Depends(get_session)):
    """Получение составного заказа по ID"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        compose_order = await crud.get_compose_order_by_id(db, order_id)
        if not compose_order or compose_order.user_id != user_id:
            raise HTTPException(status_code=404, detail=f"Составной заказ с id={order_id} не найден или не принадлежит пользователю")
        
        compose_order_data = compose_order.compose_order_data
        compose_order_data["id"] = compose_order.id
        compose_order_data["status"] = compose_order.status
        
        return compose_order_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении составного заказа по id: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении заказа: {str(e)}")

@app.delete("/api/compose_order/{order_id}")
async def delete_compose_order_by_id(request: Request, order_id: int, db: AsyncSession = Depends(get_session)):
    """Удаление составного заказа по ID"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        await crud.delete_compose_order_by_id(db, order_id, user_id)
        await db.commit()
        logger.info(f"Составной заказ id={order_id} успешно удалён")
        return {"success": True}
    except Exception as e:
        logger.error(f"Ошибка при удалении составного заказа: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении заказа: {str(e)}")

@app.post("/api/compose_order/{order_id}/generate-pdf")
async def generate_compose_order_pdf(request: Request, order_id: int, db: AsyncSession = Depends(get_session)):
    """Генерация коммерческого предложения для составного заказа"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        # Получаем данные составного заказа
        compose_order = await crud.get_compose_order_by_id(db, order_id)
        if not compose_order or compose_order.user_id != user_id:
            raise HTTPException(status_code=404, detail=f"Составной заказ с id={order_id} не найден или не принадлежит пользователю")
        
        compose_order_data = compose_order.compose_order_data
        
        # Извлекаем данные из rooms
        rooms = compose_order_data.get("rooms", [])
        if not rooms:
            raise HTTPException(status_code=400, detail="В составном заказе нет данных помещений")
        
        # Формируем данные для генерации PDF
        aircon_results = []
        components = []
        
        for i, room in enumerate(rooms):
            selected_aircons = room.get("selected_aircons_for_room", [])
            
            # Обрабатываем кондиционеры
            if isinstance(selected_aircons, str):
                try:
                    selected_aircons = json.loads(selected_aircons)
                except json.JSONDecodeError:
                    logger.error(f"Ошибка парсинга JSON для selected_aircons в помещении {i+1}")
                    selected_aircons = []
            
            if not isinstance(selected_aircons, list):
                selected_aircons = []
            
            for ac_string in selected_aircons:
                if isinstance(ac_string, str):
                    # Парсим строку формата "Бренд | модель | мощность | цена"
                    parts = ac_string.split(" | ")
                    if len(parts) >= 4:
                        aircon_results.append({
                            "brand": parts[0],
                            "model_name": parts[1],
                            "cooling_power_kw": parts[2].replace(" кВт", ""),
                            "retail_price_byn": parts[3].replace(" BYN", "")
                        })
            
            # Обрабатываем комплектующие
            room_components = room.get("components_for_room", [])
            components.extend(room_components)
        
        # Извлекаем данные клиента и скидку
        client_data = compose_order_data.get("client_data", {})
        discount_percent = client_data.get("discount", 0)
        
        # Генерируем PDF
        from utils.compose_pdf_generator import generate_compose_commercial_offer_pdf
        
        pdf_path = await generate_compose_commercial_offer_pdf(
            compose_order_data, aircon_results, components, discount_percent, db
        )
        
        logger.info(f"КП для составного заказа {order_id} успешно сгенерировано: {pdf_path}")
        return {"success": True, "pdf_path": pdf_path}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации КП для составного заказа: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации коммерческого предложения: {str(e)}")

@app.post("/api/save_compose_order/")
async def save_compose_order_endpoint(request: Request, payload: dict, db: AsyncSession = Depends(get_session)):
    """Сохранение составного заказа"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        order_id = payload.get("id")
        compose_order_data = payload.get("compose_order_data", {})
        status = payload.get("status", "draft")
        components_update = payload.get("components", [])
        
        # Распределяем компоненты по комнатам на основе метаданных
        if components_update:
            # Инициализируем rooms если их нет
            if "rooms" not in compose_order_data:
                compose_order_data["rooms"] = []
            
            # Группируем компоненты по room_index
            components_by_room = {}
            components_without_room = []
            
            for component in components_update:
                # Каждый компонент должен содержать room_index, указывающий на комнату
                room_idx = component.get("room_index")
                
                # Валидация room_index
                if room_idx is None:
                    logger.warning(f"Компонент без указания room_index будет присвоен первой комнате: {component.get('name', 'неизвестный')}")
                    components_without_room.append(component)
                    room_idx = 0
                elif not isinstance(room_idx, int) or room_idx < 0:
                    logger.error(f"Некорректный room_index={room_idx} для компонента {component.get('name', 'неизвестный')}, присваиваем 0")
                    room_idx = 0
                
                if room_idx not in components_by_room:
                    components_by_room[room_idx] = []
                components_by_room[room_idx].append(component)
            
            # Логируем предупреждение если есть компоненты без room_index
            if components_without_room:
                logger.warning(f"Найдено {len(components_without_room)} компонентов без room_index, они присвоены комнате 0")
            
            # Валидация: проверяем, что индексы комнат не превышают разумные пределы
            max_room_idx = max(components_by_room.keys()) if components_by_room else 0
            if max_room_idx > 100:  # Защита от случайных больших значений
                logger.error(f"Обнаружен слишком большой индекс комнаты: {max_room_idx}, это может быть ошибкой")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Индекс комнаты {max_room_idx} превышает допустимое значение. Проверьте корректность данных."
                )
            
            # Обновляем компоненты для каждой комнаты
            for room_idx, room_components in components_by_room.items():
                # Убедимся, что комната с таким индексом существует
                while len(compose_order_data["rooms"]) <= room_idx:
                    compose_order_data["rooms"].append({})
                
                # Обновляем компоненты для комнаты
                compose_order_data["rooms"][room_idx]["components_for_room"] = room_components
                logger.info(f"Обновлены комплектующие для комнаты {room_idx}: {len(room_components)} элементов")
            
            logger.info(f"Всего обновлено компонентов: {len(components_update)} в {len(components_by_room)} комнатах")
        
        if order_id:
            # Обновляем существующий заказ
            existing_order = await crud.get_compose_order_by_id(db, order_id)
            if not existing_order or existing_order.user_id != user_id:
                logger.warning(f"Заказ id={order_id} не найден или не принадлежит user_id={user_id}")
                raise HTTPException(status_code=404, detail=f"Заказ с id={order_id} не найден или не принадлежит пользователю")
            
            # Объединяем данные
            existing_data = existing_order.compose_order_data.copy() if isinstance(existing_order.compose_order_data, dict) else {}
            existing_data.update(compose_order_data)
            
            # Обновляем заказ
            existing_order.compose_order_data = existing_data
            existing_order.status = status
            
            # Коммитим изменения перед возвратом
            await db.commit()
            await db.refresh(existing_order)
            
            logger.info(f"Обновлен составной заказ id={existing_order.id} для user_id={user_id}")
            return {"success": True, "order_id": existing_order.id, "updated": True}
        else:
            # Создаем новый заказ, если order_id не предоставлен
            logger.info(f"Создание нового составного заказа для user_id={user_id}")
            
            new_order = await crud.create_compose_order_simple(
                db=db,
                user_id=user_id,
                compose_order_data=compose_order_data,
                status=status
            )
            
            logger.info(f"Создан новый составной заказ id={new_order.id} для user_id={user_id}")
            return {"success": True, "order_id": new_order.id, "created": True}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при сохранении составного заказа для user_id={user_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении заказа: {str(e)}")