"""
Минимальный файл бэкенда с только необходимыми эндпоинтами.
Включает аутентификацию, мониторинг и основные функции для new_front.py.
"""
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import datetime
import re
from db import crud, schemas
from db.database import get_session, AsyncSessionLocal, engine
from utils.mylogger import Logger
from utils.graceful_degradation import graceful_fallback, graceful_manager
from db.schemas import FullOrderCreate, UserCreate, UserLogin, TokenResponse, UserResponse
from utils.auth import hash_password, verify_password, generate_token, get_token_expiry, verify_secret_key
from utils.auth_middleware import auth_middleware, get_user_id_from_request, get_username_from_request
import json
from sqlalchemy import select
import time
import asyncio

logger = Logger(name=__name__, log_file="backend.log")
app = FastAPI(title="Air-Con Commercial Offer API", version="0.1.0")

# Добавляем middleware для аутентификации
app.middleware("http")(auth_middleware)

# Глобальный обработчик исключений
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Необработанное исключение: {exc}", exc_info=True)
    return {"error": "Внутренняя ошибка сервера", "detail": str(exc)}

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
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
        
        return {
            "status": "healthy", 
            "database": "connected",
            "pool_stats": pool_stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

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
        token_data = {
            "user_id": user.id,
            "username": user.username,
            "exp": get_token_expiry()
        }
        token = generate_token(token_data)
        
        logger.info(f"Пользователь {user.username} успешно зарегистрирован")
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            username=user.username
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
        token_data = {
            "user_id": user.id,
            "username": user.username,
            "exp": get_token_expiry()
        }
        token = generate_token(token_data)
        
        logger.info(f"Пользователь {user.username} успешно аутентифицирован")
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            username=user.username
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
async def recreate_connection_pool():
    """Эндпоинт для пересоздания пула соединений"""
    try:
        from db.database import _recreate_connection_pool
        await _recreate_connection_pool()
        return {"status": "success", "message": "Пул соединений пересоздан"}
    except Exception as e:
        logger.error(f"Ошибка при пересоздании пула: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/cleanup_pool")
async def cleanup_connection_pool():
    """Эндпоинт для graceful очистки пула соединений"""
    try:
        from db.database import engine
        pool = engine.pool
        
        # Получаем статистику до очистки
        before_stats = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
        
        logger.info(f"Начинаем graceful очистку пула. Текущее состояние: {before_stats}")
        
        # Graceful shutdown: закрываем пул для новых соединений
        await engine.dispose()
        
        # Ждем завершения активных соединений
        await asyncio.sleep(2)
        
        # Получаем статистику после очистки
        after_stats = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
        
        logger.info(f"Graceful очистка пула завершена. Состояние после: {after_stats}")
        
        return {
            "status": "success", 
            "message": "Пул соединений очищен gracefully",
            "before_stats": before_stats,
            "after_stats": after_stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Ошибка при graceful очистке пула: {e}")
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

@app.post("/api/save_order/")
async def save_order_endpoint(request: Request, payload: dict, db: AsyncSession = Depends(get_session)):
    """Сохранение обычного заказа (для совместимости)"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        # Определяем режим: только КП, только components, или оба
        has_kp = 'client_data' in payload and 'order_params' in payload and 'aircon_params' in payload
        has_components = 'components' in payload
        order_id = payload.get('id')
        
        if not has_kp and not has_components:
            return {"success": False, "error": "Нет данных для сохранения"}
        
        # Если есть ID заказа, пытаемся найти существующий
        order = None
        if order_id:
            order = await crud.get_order_by_id(db, order_id)
        
        # Если нет заказа и есть данные для КП, создаем новый
        if not order and has_kp:
            from datetime import date
            order_data = {k: payload[k] for k in ("client_data", "order_params", "aircon_params") if k in payload}
            order_payload = FullOrderCreate(
                user_id=user_id,
                order_data=order_data,
                status=payload.get("status", "draft")
            )
            order = await crud.create_order(db, order_payload)
            logger.info(f"Создан новый заказ с id={order.id}")
            return {"success": True, "order_id": order.id, "updated": False}
        
        # Если заказ есть — обновить только нужные поля
        if order:
            if has_components:
                # Обновляем только components
                updated_data = order.order_data.copy()
                updated_data["components"] = payload["components"]
                order.order_data = updated_data
                order.status = payload.get("status", order.status)
            
            await db.commit()
            logger.info(f"Обновлён заказ id={order.id}. Итоговое order_data: {order.order_data}")
            return {"success": True, "order_id": order.id, "updated": True}
        
        logger.error("Не удалось найти или создать заказ для обновления.")
        return {"success": False, "error": "Не удалось найти или создать заказ."}
    except Exception as e:
        logger.error(f"Ошибка при сохранении/обновлении заказа: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера при обработке заказа: {e}")

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
        return {"success": False, "error": str(e)}

@app.get("/api/compose_order/{order_id}")
async def get_compose_order_by_id(request: Request, order_id: int, db: AsyncSession = Depends(get_session)):
    """Получение составного заказа по ID"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        compose_order = await crud.get_compose_order_by_id(db, order_id)
        if not compose_order or compose_order.user_id != user_id:
            return {"error": f"Составной заказ с id={order_id} не найден или не принадлежит пользователю"}
        
        compose_order_data = compose_order.compose_order_data
        compose_order_data["id"] = compose_order.id
        compose_order_data["status"] = compose_order.status
        
        return compose_order_data
    except Exception as e:
        logger.error(f"Ошибка при получении составного заказа по id: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

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
        return {"success": False, "error": str(e)}

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
        
        # Если есть компоненты для обновления, сохраняем их в rooms[0].components_for_room
        if components_update:
            if "rooms" not in compose_order_data:
                compose_order_data["rooms"] = [{}]
            if len(compose_order_data["rooms"]) == 0:
                compose_order_data["rooms"].append({})
            
            compose_order_data["rooms"][0]["components_for_room"] = components_update
            logger.info(f"Обновлены комплектующие для помещения: {len(components_update)} элементов")
        
        if order_id:
            # Обновляем существующий заказ
            existing_order = await crud.get_compose_order_by_id(db, order_id)
            if not existing_order or existing_order.user_id != user_id:
                return {"success": False, "error": f"Заказ с id={order_id} не найден или не принадлежит пользователю"}
            
            # Объединяем данные
            existing_data = existing_order.compose_order_data.copy()
            existing_data.update(compose_order_data)
            
            existing_order.compose_order_data = existing_data
            existing_order.status = status
            
            await db.commit()
            return {"success": True, "order_id": order.id, "updated": True}
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении составного заказа: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/generate_compose_offer/")
async def generate_compose_offer_endpoint(request: Request, payload: dict, db: AsyncSession = Depends(get_session)):
    """Генерация коммерческого предложения для составного заказа"""
    try:
        user_id = get_user_id_from_request(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Требуется аутентификация")
        
        order_id = payload.get("id")
        if not order_id:
            return {"error": "Не указан ID заказа"}
        
        # Получаем данные составного заказа
        compose_order = await crud.get_compose_order_by_id(db, order_id)
        if not compose_order or compose_order.user_id != user_id:
            return {"error": f"Составной заказ с id={order_id} не найден"}
        
        compose_order_data = compose_order.compose_order_data
        
        # Извлекаем данные из rooms
        rooms = compose_order_data.get("rooms", [])
        if not rooms:
            return {"error": "В составном заказе нет данных помещений"}
        
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
        
    except Exception as e:
        logger.error(f"Ошибка при генерации КП для составного заказа: {e}", exc_info=True)
        return {"success": False, "error": str(e)}