"""
Основной файл бэкенда, реализующий API на FastAPI.
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
# Удалены неиспользуемые импорты aircon_selector и pdf_generator
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

# ... (эндпоинты startup, shutdown, read_root, get_all_air_conditioners, select_aircons_endpoint без изменений) ...
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
    logger.info("Остановка FastAPI приложения.")
    
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

@app.get("/")
async def read_root():
    logger.info("Запрос к корневому эндпоинту '/' (проверка работоспособности API)")
    return {"message": "API бэкенда для подбора кондиционеров работает."}

@app.get("/health")
@graceful_fallback("health_check", cache_key="health_status", cache_ttl=60)
async def health_check():
    """Эндпоинт для проверки здоровья приложения"""
    try:
        # Проверяем соединение с БД
        from db.database import AsyncSessionLocal, engine
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        
        # Получаем статистику пула соединений
        pool = engine.pool
        pool_stats = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
        
        return {
            "status": "healthy", 
            "database": "connected",
            "pool_stats": pool_stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# --- Аутентификация ---

@app.post("/api/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_session)):
    """
    Регистрация нового пользователя.
    """
    logger.info(f"Попытка регистрации пользователя: {user_data.username}")
    
    # Проверяем секретный ключ
    if not verify_secret_key(user_data.secret_key):
        logger.warning(f"Неверный секретный ключ при регистрации: {user_data.username}")
        raise HTTPException(status_code=400, detail="Неверный секретный ключ")
    
    # Проверяем, не существует ли уже пользователь с таким логином
    existing_user = await crud.get_user_by_username(db, user_data.username)
    if existing_user:
        logger.warning(f"Попытка регистрации существующего пользователя: {user_data.username}")
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
    
    # Хешируем пароль
    password_hash = hash_password(user_data.password)
    
    # Создаем пользователя
    try:
        user = await crud.create_user(db, user_data, password_hash)
        
        # Генерируем токен
        token = generate_token()
        expires_at = get_token_expiry()
        
        # Сохраняем токен в БД
        await crud.update_user_token(db, user.id, token, expires_at)
        
        logger.info(f"Пользователь успешно зарегистрирован: {user.username} (id={user.id})")
        
        return TokenResponse(
            token=token,
            expires_at=expires_at,
            user=UserResponse(
                id=user.id,
                username=user.username,
                created_at=user.created_at,
                last_login=user.last_login,
                is_active=user.is_active
            )
        )
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя {user_data.username}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при создании пользователя")


@app.post("/api/auth/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin, db: AsyncSession = Depends(get_session)):
    """
    Вход пользователя в систему.
    """
    logger.info(f"Попытка входа пользователя: {login_data.username}")
    
    # Ищем пользователя
    user = await crud.get_user_by_username(db, login_data.username)
    if not user:
        logger.warning(f"Попытка входа несуществующего пользователя: {login_data.username}")
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    # Проверяем пароль
    if not verify_password(login_data.password, user.password_hash):
        logger.warning(f"Неверный пароль для пользователя: {login_data.username}")
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    # Проверяем активность пользователя
    if not user.is_active:
        logger.warning(f"Попытка входа неактивного пользователя: {login_data.username}")
        raise HTTPException(status_code=401, detail="Пользователь неактивен")
    
    # Генерируем новый токен
    token = generate_token()
    expires_at = get_token_expiry()
    
    # Сохраняем токен в БД
    await crud.update_user_token(db, user.id, token, expires_at)
    
    logger.info(f"Пользователь успешно вошел в систему: {user.username} (id={user.id})")
    
    return TokenResponse(
        token=token,
        expires_at=expires_at,
        user=UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at,
            last_login=user.last_login,
            is_active=user.is_active
        )
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(request: Request, db: AsyncSession = Depends(get_session)):
    """
    Получение информации о текущем пользователе.
    """
    user_id = get_user_id_from_request(request)
    username = get_username_from_request(request)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Требуется аутентификация")
    
    logger.info(f"Запрос информации о пользователе: {username} (id={user_id})")
    
    user = await crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        created_at=user.created_at,
        last_login=user.last_login,
        is_active=user.is_active
    )

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
            "timestamp": time.time(),
            "overall_status": "error",
            "error": str(e)
        }

@app.get("/api/graceful-degradation/status")
async def get_graceful_degradation_status():
    """Эндпоинт для мониторинга состояния graceful degradation"""
    try:
        return graceful_manager.get_degradation_status()
    except Exception as e:
        logger.error(f"Graceful degradation status check failed: {e}")
        return {
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
            "message": "Восстановление выполнено" if success else "Восстановление не удалось",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Graceful recovery attempt failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/api/recreate_pool")
async def recreate_connection_pool():
    """Эндпоинт для принудительного пересоздания пула соединений"""
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
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
        
        logger.info(f"Начинаем graceful очистку пула. Текущее состояние: {before_stats}")
        
        # Graceful shutdown: закрываем пул для новых соединений
        pool.close()
        
        # Ждем завершения активных соединений (максимум 30 секунд, оптимизировано для снижения нагрузки)
        max_wait_time = 30
        wait_interval = 5  # Увеличено с 1 до 5 секунд для снижения нагрузки
        waited_time = 0
        
        while pool.checkedout() > 0 and waited_time < max_wait_time:
            logger.info(f"Ожидаем завершения {pool.checkedout()} активных соединений...")
            await asyncio.sleep(wait_interval)
            waited_time += wait_interval
        
        if pool.checkedout() > 0:
            logger.warning(f"Не удалось дождаться завершения {pool.checkedout()} соединений за {max_wait_time} секунд")
        else:
            logger.info("Все активные соединения завершены")
        
        # Теперь безопасно очищаем пул
        pool.dispose()
        
        # Получаем статистику после очистки
        after_stats = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
        
        logger.info(f"Graceful очистка пула завершена. До: {before_stats}, После: {after_stats}")
        
        return {
            "status": "success", 
            "message": "Пул соединений очищен gracefully",
            "before_stats": before_stats,
            "after_stats": after_stats,
            "waited_time": waited_time,
            "active_connections_remaining": pool.checkedout()
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

@app.get("/api/air_conditioners/", response_model=List[schemas.AirConditioner])
async def get_all_air_conditioners(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_session)):
    logger.info(f"Запрос на получение списка кондиционеров (skip={skip}, limit={limit}).")
    try:
        air_conditioners = await crud.get_air_conditioners(db, skip=skip, limit=limit)
        logger.info(f"Успешно получено {len(air_conditioners)} записей о кондиционерах.")
        return air_conditioners
    except Exception as e:
        logger.error(f"Ошибка при получении списка кондиционеров: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при получении данных.")

@app.post("/api/select_aircons/")
async def select_aircons_endpoint(payload: dict, db: AsyncSession = Depends(get_session)):
    # Логируем только ключевую информацию вместо полного payload
    if "id" in payload:
        logger.info(f"Получен запрос на эндпоинт /api/select_aircons/ для заказа ID: {payload['id']}")
    else:
        client_name = payload.get("client_data", {}).get('full_name', 'N/A')
        logger.info(f"Получен запрос на эндпоинт /api/select_aircons/ для клиента: {client_name}")
    try:
        # Если в payload только id — достаём параметры из заказа
        if list(payload.keys()) == ["id"] or ("id" in payload and len(payload) == 1):
            order_id = payload["id"]
            result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
            order = result.scalars().first()
            if not order:
                logger.error(f"Заказ с id={order_id} не найден для подбора кондиционеров!")
                return {"success": False, "error": f"Заказ с id={order_id} не найден!"}
            order_data = json.loads(order.order_data)
            aircon_params = order_data.get("aircon_params", {})
            client_full_name = order_data.get("client_data", {}).get('full_name', 'N/A')
        else:
            aircon_params = payload.get("aircon_params", {})
            client_full_name = payload.get("client_data", {}).get('full_name', 'N/A')
        
        # Преобразуем illumination из строки в число, если нужно
        if isinstance(aircon_params.get('illumination'), str):
            illumination_map = {"Слабая": 0, "Средняя": 1, "Сильная": 2}
            aircon_params['illumination'] = illumination_map.get(aircon_params['illumination'], 1)
        
        # Преобразуем activity из строки в число, если нужно
        if isinstance(aircon_params.get('activity'), str):
            activity_map = {"Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
            aircon_params['activity'] = activity_map.get(aircon_params['activity'], 0)
        
        logger.info(f"Начат подбор кондиционеров для клиента: {client_full_name}")
        # Импортируем функцию локально для совместимости
        from utils.compose_aircon_selector import select_aircons_for_params
        selected_aircons = await select_aircons_for_params(db, aircon_params)
        logger.info(f"Подобрано {len(selected_aircons)} кондиционеров.")
        aircons_list = [schemas.AirConditioner.from_orm(ac).dict() for ac in selected_aircons]
        response_data = {"aircons_list": aircons_list, "total_count": len(selected_aircons)}
        
        # Дополнительное логирование для отладки
        logger.info(f"Отправляем ответ: total_count={len(selected_aircons)}, aircons_list length={len(aircons_list)}")
        if selected_aircons:
            logger.info(f"Первые 3 кондиционера: {[f'{ac.brand} {ac.model_name}' for ac in selected_aircons[:3]]}")
        
        logger.info("Подбор кондиционеров завершён успешно.")
        return response_data
    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при подборе кондиционеров: {e}")


# --- Эндпоинт для генерации КП (С УЛУЧШЕНИЕМ) ---
@app.post("/api/generate_offer/")
async def generate_offer_endpoint(payload: dict, db: AsyncSession = Depends(get_session)):
    # Логируем только ключевую информацию вместо полного payload
    if "id" in payload:
        logger.info(f"Получен запрос на эндпоинт /api/generate_offer/ для заказа ID: {payload['id']}")
    else:
        client_name = payload.get("client_data", {}).get('full_name', 'N/A')
        logger.info(f"Получен запрос на эндпоинт /api/generate_offer/ для клиента: {client_name}")
    try:
        # Если в payload только id — подгружаем все данные заказа из базы
        if list(payload.keys()) == ["id"] or ("id" in payload and len(payload) == 1):
            order_id = payload["id"]
            result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
            order = result.scalars().first()
            if not order:
                logger.error(f"Заказ с id={order_id} не найден для генерации КП!")
                return {"success": False, "error": f"Заказ с id={order_id} не найден!"}
            order_data = json.loads(order.order_data)
            client_data = order_data.get("client_data", {})
            order_params = order_data.get("order_params", {})
            aircon_params = order_data.get("aircon_params", {})
            components = order_data.get("components", [])
            client_full_name = client_data.get('full_name', 'N/A')
        else:
            client_data = payload.get("client_data", {})
            order_params = payload.get("order_params", {})
            aircon_params = payload.get("aircon_params", {})
            components = payload.get("components", [])
            client_full_name = client_data.get('full_name', 'N/A')
        discount = order_params.get("discount", 0)
        # 1. Создание или поиск клиента
        client_phone = client_data.get("phone")
        if not client_phone:
            raise HTTPException(status_code=400, detail="Отсутствует номер телефона клиента.")
        client = await crud.get_client_by_phone(db, client_phone)
        if not client:
            client = await crud.create_client(db, schemas.ClientCreate(**client_data))
        # 2. Подбор кондиционеров
        # Преобразуем illumination из строки в число, если нужно
        if isinstance(aircon_params.get('illumination'), str):
            illumination_map = {"Слабая": 0, "Средняя": 1, "Сильная": 2}
            aircon_params['illumination'] = illumination_map.get(aircon_params['illumination'], 1)
        
        # Преобразуем activity из строки в число, если нужно
        if isinstance(aircon_params.get('activity'), str):
            activity_map = {"Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
            aircon_params['activity'] = activity_map.get(aircon_params['activity'], 0)
        
        # Импортируем функцию локально для совместимости
        from utils.compose_aircon_selector import select_aircons_for_params
        selected_aircons = await select_aircons_for_params(db, aircon_params)
        # --- Формируем варианты для PDF ---
        aircon_variants = []
        variant_items = []
        for ac in selected_aircons:
            ac_dict = schemas.AirConditioner.from_orm(ac).dict()
            specs = []
            if ac_dict.get('cooling_power_kw'): specs.append(f"Охлаждение: {ac_dict['cooling_power_kw']} кВт")
            if ac_dict.get('is_inverter'): specs.append("Инверторный")
            if ac_dict.get('has_wifi'): specs.append("Wi-Fi")
            description = ac_dict.get('description', '')
            # В новой структуре описание уже содержит всю информацию
            # Добавляем описание как есть, если оно есть
            if description:
                specs.append(description)
            variant_items.append({
                'name': f"{ac_dict.get('brand', '')} {ac_dict.get('model_name', '')}",
                'manufacturer': ac_dict.get('brand', ''),
                'price': ac_dict.get('retail_price_byn', 0),
                'qty': 1, 'unit': 'шт.', 'delivery': 'в наличии',
                'discount_percent': float(order_params.get('discount', 0)),
                'specifications': specs,
                'short_description': "",
                'image_path': ac_dict.get('image_path', '')
            })
        aircon_variants.append({
            'title': 'Варианты оборудования, подходящие по параметрам',
            'description': '',
            'items': variant_items
        })
        # 1. Оставляем только выбранные комплектующие (selected=True и qty>0 или length>0)
        components_for_pdf = []
        for comp in components:
            if comp.get('selected') and (comp.get('qty', 0) > 0 or comp.get('length', 0) > 0):
                comp_new = comp.copy()
                comp_new.setdefault('unit', 'шт.')
                comp_new.setdefault('discount_percent', discount)
                components_for_pdf.append(comp_new)
        today = datetime.date.today().strftime('%d_%m_%Y')
        # 2. Имя клиента для offer_number: только запрещённые для имени файла символы заменяем на '_', буквы и пробелы оставляем
        import re
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', client_full_name).strip()[:20]
        offer_number = f"{today}_{safe_name}"
        # 4. Генерируем PDF (ЗАКОММЕНТИРОВАНО - используется только для составных заказов)
        # pdf_path = await generate_commercial_offer_pdf_async(
        #     client_data=client_data, order_params=order_params,
        #     aircon_variants=aircon_variants, components=components_for_pdf,
        #     discount_percent=discount, offer_number=offer_number, db_session=db
        # )
        return {"success": False, "error": "Генерация PDF для обычных заказов отключена. Используйте составные заказы."}
        # --- Меняем статус заказа на completed, если заказ найден по id ---
        if 'order' in locals() and order is not None:
            order.status = 'completed'
            order.pdf_path = pdf_path
            await db.commit()
        response_data = {
            "aircon_variants": aircon_variants,
            "total_count": len(selected_aircons),
            "client_name": client.full_name,
            "components": components_for_pdf,
            "pdf_path": pdf_path
        }
        return response_data
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Ошибка при формировании КП: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при формировании КП: {e}")

# --- Новый эндпоинт для сохранения заказа-черновика ---

@app.post("/api/save_order/")
async def save_order_endpoint(payload: dict, db: AsyncSession = Depends(get_session)):
    # Логируем только ключевую информацию вместо полного payload
    if "id" in payload:
        logger.info(f"Получен запрос на эндпоинт /api/save_order/ для заказа ID: {payload['id']}")
    else:
        client_name = payload.get("client_data", {}).get('full_name', 'N/A')
        logger.info(f"Получен запрос на эндпоинт /api/save_order/ для клиента: {client_name}")
    try:
        # --- Новый режим: только комментарий ---
        if list(payload.keys()) == ["id", "comment"] or ("id" in payload and "comment" in payload and len(payload) == 2):
            order_id = payload["id"]
            comment = payload["comment"]
            
            # Сначала ищем в обычных заказах
            result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
            order = result.scalars().first()
            
            # Если не найден в обычных заказах, ищем в составных
            if not order:
                result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
                compose_order = result.scalars().first()
                if not compose_order:
                    logger.error(f"Заказ с id={order_id} не найден для обновления комментария!")
                    return {"success": False, "error": f"Заказ с id={order_id} не найден!"}
                
                # Обновляем комментарий для составного заказа
                compose_order_data = json.loads(compose_order.compose_order_data)
                compose_order_data["comment"] = comment
                compose_order.compose_order_data = json.dumps(compose_order_data, ensure_ascii=False)
                await db.commit()
                logger.info(f"Комментарий для составного заказа id={order_id} успешно обновлён.")
                return {"success": True, "order_id": compose_order.id, "updated": True}
            
            # Обновляем комментарий для обычного заказа
            order_data = json.loads(order.order_data)
            order_data["comment"] = comment
            order.order_data = json.dumps(order_data, ensure_ascii=False)
            await db.commit()
            logger.info(f"Комментарий для заказа id={order_id} успешно обновлён.")
            return {"success": True, "order_id": order.id, "updated": True}
        # Определяем режим: только КП, только components, или оба
        has_kp = 'client_data' in payload and 'order_params' in payload and 'aircon_params' in payload
        has_components = 'components' in payload
        logger.info(f"Режим сохранения: КП={has_kp}, components={has_components}")
        # 1. Найти или создать клиента (если есть client_data)
        client = None
        if has_kp:
            client_data = payload["client_data"]
            client = await crud.get_client_by_phone(db, client_data["phone"])
            if not client:
                client = await crud.create_client(db, schemas.ClientCreate(**client_data))
        # 2. Получить существующий заказ, если есть id
        order_id = payload.get("id")
        order = None
        if order_id is not None:
            result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
            order = result.scalars().first()
            logger.info(f"Найден заказ с id={order_id}: {bool(order)}")
        # 3. Если заказа нет и есть КП-данные — создать новый заказ
        if not order and has_kp:
            from datetime import date
            order_data = {k: payload[k] for k in ("client_data", "order_params", "aircon_params") if k in payload}
            if has_components:
                order_data["components"] = payload["components"]
            order_payload = schemas.OrderCreate(
                client_id=client.id,
                created_at=date.today(),
                status=payload.get("status", "draft"),
                pdf_path=None,
                order_data=order_data
            )
            order = await crud.create_order(db, order_payload)
            logger.info(f"Создан новый заказ с id={order.id}")
            return {"success": True, "order_id": order.id, "updated": False}
        # 4. Если заказ есть — обновить только нужные поля
        if order:
            order_data = json.loads(order.order_data)
            if has_kp:
                for k in ("client_data", "order_params", "aircon_params"):
                    if k in payload:
                        order_data[k] = payload[k]
            if has_components:
                order_data["components"] = payload["components"]
            order.order_data = json.dumps(order_data, ensure_ascii=False)
            order.status = payload.get("status", order.status)
            await db.commit()
            logger.info(f"Обновлён заказ id={order.id}. Итоговое order_data: {order.order_data}")
            return {"success": True, "order_id": order.id, "updated": True}
        logger.error("Не удалось найти или создать заказ для обновления.")
        return {"success": False, "error": "Не удалось найти или создать заказ."}
    except Exception as e:
        logger.error(f"Ошибка при сохранении/обновлении заказа: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера при обработке заказа: {e}")

# --- Эндпоинт: получить список всех заказов (id, имя, дата, адрес, статус) ---
@app.get("/api/orders/")
async def get_orders_list(db: AsyncSession = Depends(get_session)):
    """
    Возвращает список всех заказов для фронта.
    Сначала идут заказы в статусе 'draft' или 'forming' (редактируются), затем остальные.
    Внутри групп сортировка по дате создания (новые выше).
    Логирует результат и ошибки.
    """
    try:
        result = await db.execute(select(crud.models.Order))
        orders = result.scalars().all()
        logger.info(f"Всего заказов в базе: {len(orders)}")
        result = []
        for order in orders:
            order_data = json.loads(order.order_data)
            client_data = order_data.get("client_data", {})
            result.append({
                "id": order.id,
                "order_type": order.order_type or "Order",  # Добавляем тип заказа
                "client_name": client_data.get("full_name", ""),
                "address": client_data.get("address", ""),
                "created_at": order.created_at.strftime("%Y-%m-%d"),
                "status": order.status,
                "comment": order_data.get("comment", "")
            })
        logger.info(f"Отправлен список заказов: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении списка заказов: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# --- Эндпоинт: получить список всех составных заказов ---
@app.get("/api/compose_orders/")
async def get_compose_orders_list(db: AsyncSession = Depends(get_session)):
    """
    Возвращает список всех составных заказов для фронта.
    """
    try:
        result = await db.execute(select(crud.models.ComposeOrder))
        compose_orders = result.scalars().all()
        logger.info(f"Всего составных заказов в базе: {len(compose_orders)}")
        result = []
        for order in compose_orders:
            compose_order_data = json.loads(order.compose_order_data)
            client_data = compose_order_data.get("client_data", {})
            result.append({
                "id": order.id,
                "order_type": order.order_type or "Compose",  # Тип составного заказа
                "client_name": client_data.get("full_name", ""),
                "address": client_data.get("address", ""),
                "created_at": order.created_at.strftime("%Y-%m-%d"),
                "status": order.status,
                "comment": compose_order_data.get("comment", "")  # Загружаем комментарий для составных заказов
            })
        logger.info(f"Отправлен список составных заказов: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении списка составных заказов: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# --- Эндпоинт: получить объединенный список всех заказов ---
@app.get("/api/all_orders/")
@graceful_fallback("orders_list", cache_key="all_orders_list", cache_ttl=300)
async def get_all_orders_list(db: AsyncSession = Depends(get_session)):
    """
    Возвращает объединенный список всех заказов (обычных и составных) для фронта.
    """
    try:
        logger.info("=== /api/all_orders/ вызван ===")
        # Получаем обычные заказы
        result = await db.execute(select(crud.models.Order))
        orders = result.scalars().all()
        
        # Получаем составные заказы
        result = await db.execute(select(crud.models.ComposeOrder))
        compose_orders = result.scalars().all()
        
        logger.info(f"Всего заказов в базе: {len(orders)} обычных, {len(compose_orders)} составных")
        
        all_orders = []
        
        # Добавляем обычные заказы
        for order in orders:
            logger.info(f"Обрабатываем обычный заказ id={order.id}")
            order_data = json.loads(order.order_data)
            client_data = order_data.get("client_data", {})
            all_orders.append({
                "id": order.id,
                "order_type": order.order_type or "Order",
                "client_name": client_data.get("full_name", ""),
                "address": client_data.get("address", ""),
                "created_at": order.created_at.strftime("%Y-%m-%d"),
                "status": order.status,
                "comment": order_data.get("comment", "")
            })
        
        # Добавляем составные заказы
        for order in compose_orders:
            logger.info(f"Обрабатываем составной заказ id={order.id}")
            compose_order_data = json.loads(order.compose_order_data)
            client_data = compose_order_data.get("client_data", {})
            all_orders.append({
                "id": order.id,
                "order_type": order.order_type or "Compose",
                "client_name": client_data.get("full_name", ""),
                "address": client_data.get("address", ""),
                "created_at": order.created_at.strftime("%Y-%m-%d"),
                "status": order.status,
                "comment": compose_order_data.get("comment", "")  # Загружаем комментарий для составных заказов
            })
        
        # Сортируем по дате создания (новые выше)
        all_orders.sort(key=lambda x: x["created_at"], reverse=True)
        
        logger.info(f"Отправлен объединенный список заказов: {len(all_orders)} заказов")
        logger.info(f"Детали заказов: {all_orders}")
        return all_orders
    except Exception as e:
        logger.error(f"Ошибка при получении объединенного списка заказов: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# --- Эндпоинт: получить заказ по ID ---
@app.get("/api/order/{order_id}")
async def get_order_by_id(order_id: int = Path(...), db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"success": False, "error": "Заказ не найден"}
        # Возвращаем order_data как есть (словарь)
        order_data = json.loads(order.order_data)
        order_data["id"] = order.id
        order_data["status"] = order.status
        order_data["pdf_path"] = order.pdf_path
        order_data["created_at"] = order.created_at.strftime("%Y-%m-%d")
        # comment уже будет в order_data, если есть
        return order_data
    except Exception as e:
        logger.error(f"Ошибка при получении заказа по id: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# --- Эндпоинт: получить составной заказ по ID ---
@app.get("/api/compose_order/{order_id}")
async def get_compose_order_by_id(order_id: int = Path(...), db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"success": False, "error": "Составной заказ не найден"}
        # Возвращаем compose_order_data как есть (словарь)
        compose_order_data = json.loads(order.compose_order_data)
        compose_order_data["id"] = order.id
        compose_order_data["status"] = order.status
        compose_order_data["pdf_path"] = order.pdf_path
        compose_order_data["created_at"] = order.created_at.strftime("%Y-%m-%d")
        return compose_order_data
    except Exception as e:
        logger.error(f"Ошибка при получении составного заказа по id: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# --- Эндпоинт: удалить заказ по ID ---
@app.delete("/api/order/{order_id}")
async def delete_order(order_id: int = Path(...), db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"success": False, "error": "Заказ не найден"}
        await db.delete(order)
        await db.commit()
        logger.info(f"Заказ id={order_id} успешно удалён")
        return {"success": True}
    except Exception as e:
        logger.error(f"Ошибка при удалении заказа: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.delete("/api/compose_order/{order_id}")
async def delete_compose_order(order_id: int = Path(...), db: AsyncSession = Depends(get_session)):
    """Удаляет составной заказ по ID"""
    try:
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"success": False, "error": "Составной заказ не найден"}
        await db.delete(order)
        await db.commit()
        logger.info(f"Составной заказ id={order_id} успешно удалён")
        return {"success": True}
    except Exception as e:
        logger.error(f"Ошибка при удалении составного заказа: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# --- Эндпоинты для составных заказов ---

@app.post("/api/save_compose_order/")
async def save_compose_order(payload: dict, db: AsyncSession = Depends(get_session)):
    """
    Сохраняет или обновляет составной заказ с новой структурой данных (airs + components).
    """
    # Логируем только ключевую информацию вместо полного payload
    if "id" in payload:
        logger.info(f"Получен запрос на сохранение составного заказа ID: {payload['id']}")
    else:
        logger.info("Получен запрос на создание нового составного заказа")
    try:
        compose_order_data = payload.get("compose_order_data", {})
        # Убираем подробное логирование compose_order_data
        client_data = compose_order_data.get("client_data", {})
        
        # Проверяем, есть ли обновление комплектующих
        components_update = payload.get("components")
        room_config = payload.get("room_config", "Базовая конфигурация")  # Получаем информацию о конфигурации
        status_update = payload.get("status")
        
        # Проверяем, есть ли обновление комментария
        comment_update = payload.get("comment")
        
        # Проверяем, есть ли обновление последнего кондиционера
        update_last_aircon = payload.get("update_last_aircon")
        
        # Проверяем обязательные поля (только если есть client_data и нет update_last_aircon)
        if client_data and not update_last_aircon and (not client_data.get("full_name") or not client_data.get("phone")):
            return {"success": False, "error": "Имя клиента и телефон обязательны"}
        
        # Ищем или создаем клиента (только если есть client_data)
        client = None
        if client_data:
            client = await crud.get_or_create_client(db, client_data)
        
        # Проверяем, есть ли уже составной заказ с таким ID
        order_id = payload.get("id")
        order = None
        if order_id:
            result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
            order = result.scalars().first()
        
        if not order:
            # Создаем новый составной заказ с новой структурой (только если есть client_data)
            if not client_data:
                return {"success": False, "error": "Для создания нового заказа необходимы данные клиента"}
            
            from datetime import date
            
            # Используем данные из payload, которые уже содержат первый кондиционер
            new_order_data = compose_order_data
            
            # Убеждаемся, что есть все необходимые поля
            if "order_params" not in new_order_data:
                new_order_data["order_params"] = {}
            if "airs" not in new_order_data:
                new_order_data["airs"] = []
            if "components" not in new_order_data:
                new_order_data["components"] = []
            if "comment" not in new_order_data:
                new_order_data["comment"] = "Оставьте комментарий..."
            if "status" not in new_order_data:
                new_order_data["status"] = "draft"
            
            order_payload = schemas.ComposeOrderCreate(
                client_id=client.id,
                created_at=date.today(),
                status=payload.get("status", "draft"),
                pdf_path=None,
                compose_order_data=new_order_data
            )
            order = await crud.create_compose_order(db, order_payload)
            logger.info(f"Создан новый составной заказ с id={order.id}")
            return {"success": True, "order_id": order.id, "updated": False}
        else:
            # Обновляем существующий заказ
            if components_update is not None:
                # Обновляем комплектующие в правильном помещении согласно room_config
                existing_data = json.loads(order.compose_order_data)
                
                # Убеждаемся, что есть массив rooms
                if "rooms" not in existing_data or not existing_data["rooms"]:
                    existing_data["rooms"] = [{}]
                
                # Находим правильное помещение для сохранения комплектующих
                target_room_index = 0  # По умолчанию первое помещение (базовая конфигурация)
                
                if room_config == "Базовая конфигурация":
                    # Для базовой конфигурации используем rooms[0]
                    target_room_index = 0
                    if len(existing_data["rooms"]) == 0:
                        existing_data["rooms"].append({})
                else:
                    # Ищем помещение с нужным room_type
                    found = False
                    for i, room in enumerate(existing_data["rooms"]):
                        if room.get("room_type") == room_config:
                            target_room_index = i
                            found = True
                            break
                    
                    if not found:
                        logger.warning(f"Помещение с room_type '{room_config}' не найдено, сохраняем в первое помещение")
                        target_room_index = 0
                
                # Сохраняем комплектующие в найденное помещение
                existing_data["rooms"][target_room_index]["components_for_room"] = components_update
                logger.info(f"Сохранены комплектующие в помещение с индексом {target_room_index} (конфигурация: {room_config})")
                
                if status_update:
                    existing_data["status"] = status_update
                if comment_update is not None:
                    existing_data["comment"] = comment_update
                    
                order.compose_order_data = json.dumps(existing_data, ensure_ascii=False)
                order.status = status_update or order.status
                logger.info(f"Обновлены комплектующие для помещения в составном заказе id={order.id}")
            elif comment_update is not None:
                # Обновляем только комментарий
                existing_data = json.loads(order.compose_order_data)
                existing_data["comment"] = comment_update
                if status_update:
                    existing_data["status"] = status_update
                order.compose_order_data = json.dumps(existing_data, ensure_ascii=False)
                order.status = status_update or order.status
                logger.info(f"Обновлен комментарий составного заказа id={order.id}")
            elif update_last_aircon is not None:
                # Обновляем только последний кондиционер
                existing_data = json.loads(order.compose_order_data)
                airs = existing_data.get("airs", [])
                logger.info(f"Обновление последнего кондиционера: найдено {len(airs)} кондиционеров в заказе")
                if airs:
                    # Обновляем параметры последнего кондиционера
                    last_air = airs[-1]
                    logger.info(f"Обновляем кондиционер с ID: {last_air.get('id')}")
                    
                    # Безопасное преобразование типов для order_params
                    order_params = update_last_aircon.get("order_params", {})
                    # Убираем подробное DEBUG логирование
                    safe_order_params = {}
                    for key, value in order_params.items():
                        if key in ["room_area", "installation_price"]:
                            try:
                                safe_order_params[key] = float(value) if value is not None else 0.0
                            except (ValueError, TypeError):
                                safe_order_params[key] = 0.0
                        elif key == "discount":
                            try:
                                safe_order_params[key] = int(float(value)) if value is not None else 0
                            except (ValueError, TypeError):
                                safe_order_params[key] = 0
                        else:
                            safe_order_params[key] = value
                    
                    # Безопасное преобразование типов для aircon_params
                    aircon_params = update_last_aircon.get("aircon_params", {})
                    # Убираем подробное DEBUG логирование
                    safe_aircon_params = {}
                    for key, value in aircon_params.items():
                        if key in ["area", "ceiling_height", "other_power", "price_limit"]:
                            try:
                                safe_aircon_params[key] = float(value) if value is not None else 0.0
                            except (ValueError, TypeError):
                                safe_aircon_params[key] = 0.0
                        elif key in ["num_people", "num_computers", "num_tvs"]:
                            try:
                                safe_aircon_params[key] = int(float(value)) if value is not None else 0
                            except (ValueError, TypeError):
                                safe_aircon_params[key] = 0
                        elif key in ["inverter", "wifi"]:
                            try:
                                safe_aircon_params[key] = bool(value) if value is not None else False
                            except (ValueError, TypeError):
                                safe_aircon_params[key] = False
                        else:
                            safe_aircon_params[key] = value
                    
                    # Убираем подробное DEBUG логирование
                    
                    last_air["order_params"] = safe_order_params
                    last_air["aircon_params"] = safe_aircon_params
                    order.compose_order_data = json.dumps(existing_data, ensure_ascii=False)
                    order.status = status_update or order.status
                    logger.info(f"Обновлен последний кондиционер составного заказа id={order.id}")
                else:
                    return {"success": False, "error": "В заказе нет кондиционеров для обновления"}
            else:
                # Обновляем полные данные заказа
                order.compose_order_data = json.dumps(compose_order_data, ensure_ascii=False)
                order.status = payload.get("status", order.status)
                logger.info(f"Обновлён составной заказ id={order.id}")
            
            await db.commit()
            return {"success": True, "order_id": order.id, "updated": True}
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении составного заказа: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/select_compose_aircons/")
async def select_compose_aircons(payload: dict, db: AsyncSession = Depends(get_session)):
    """
    Подбирает кондиционеры для последнего добавленного кондиционера в составном заказе.
    """
    # Логируем только ключевую информацию вместо полного payload
    order_id = payload.get("id")
    logger.info(f"Получен запрос на подбор кондиционеров для составного заказа ID: {order_id}")
    try:
        order_id = payload.get("id")
        if not order_id:
            return {"success": False, "error": "ID составного заказа не указан"}
        
        # Получаем составной заказ
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"success": False, "error": "Составной заказ не найден"}
        
        compose_order_data = json.loads(order.compose_order_data)
        rooms = compose_order_data.get("rooms", [])
        
        if not rooms:
            return {"success": False, "error": "В составном заказе нет данных о помещениях для подбора"}
        
        # Берем первое помещение (пока работаем с одним помещением)
        room_data = rooms[0]
        logger.info(f"Подбираем кондиционеры для помещения: {room_data.get('room_type', 'Помещение')}")
        
        # Импортируем функцию подбора для одного кондиционера
        from utils.compose_aircon_selector import select_aircons_for_params
        
        # Подбираем кондиционеры для помещения
        aircon_params = {
            "area": room_data.get("area", 0),
            "brand": room_data.get("brand", "Любой"),
            "wifi": room_data.get("wifi", False),
            "inverter": room_data.get("inverter", False),
            "price_limit": room_data.get("price_limit", 10000),
            "mount_type": room_data.get("mount_type", "Любой"),
            "ceiling_height": room_data.get("ceiling_height", 2.7),
            "illumination": room_data.get("illumination", "Средняя"),
            "num_people": room_data.get("num_people", 1),
            "activity": room_data.get("activity", "Сидячая работа"),
            "num_computers": room_data.get("num_computers", 0),
            "num_tvs": room_data.get("num_tvs", 0),
            "other_power": room_data.get("other_power", 0)
        }
        order_params = {
            "room_type": room_data.get("room_type", "Помещение"),
            "installation_price": room_data.get("installation_price", 0)
        }
        
        # Преобразуем illumination из строки в число, если нужно
        if isinstance(aircon_params.get('illumination'), str):
            illumination_map = {"Слабая": 0, "Средняя": 1, "Сильная": 2}
            aircon_params['illumination'] = illumination_map.get(aircon_params['illumination'], 1)
        
        # Преобразуем activity из строки в число, если нужно
        if isinstance(aircon_params.get('activity'), str):
            activity_map = {"Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
            aircon_params['activity'] = activity_map.get(aircon_params['activity'], 0)
        
        selected_aircons = await select_aircons_for_params(db, aircon_params)
        
        # Формируем результат для отображения
        result_text = f"Результаты подбора кондиционеров:\n"
        result_text += f"Площадь: {aircon_params.get('area', 0)} м²\n"
        
        # Рассчитываем требуемую мощность используя правильную функцию
        from utils.compose_aircon_selector import calculate_required_power
        
        # Восстанавливаем строковые значения для правильного расчета
        calculation_params = aircon_params.copy()
        if isinstance(calculation_params.get('illumination'), int):
            illumination_map = {0: "Слабая", 1: "Средняя", 2: "Сильная"}
            calculation_params['illumination'] = illumination_map.get(calculation_params['illumination'], "Средняя")
        if isinstance(calculation_params.get('activity'), int):
            activity_map = {0: "Сидячая работа", 1: "Легкая работа", 2: "Средняя работа", 3: "Тяжелая работа", 4: "Спорт"}
            calculation_params['activity'] = activity_map.get(calculation_params['activity'], "Сидячая работа")
        
        required_power = calculate_required_power(calculation_params)
        
        result_text += f"Требуемая мощность: {required_power:.2f} кВт\n"
        result_text += f"Подобрано вариантов: {len(selected_aircons)}\n\n"
        
        # Добавляем информацию о подобранных кондиционерах
        for i, ac in enumerate(selected_aircons, 1):
            result_text += f"{i}. {ac.brand} {ac.model_name}\n"
            result_text += f"   Мощность: {ac.cooling_power_kw} кВт\n"
            result_text += f"   Цена: {ac.retail_price_byn} BYN\n"
            if ac.is_inverter:
                result_text += f"   Инверторный\n"
            if ac.has_wifi:
                result_text += f"   Wi-Fi\n"
            result_text += f"   Тип кондиционера: {ac.mount_type}\n\n"
        
        # Сохраняем подобранные кондиционеры в постоянное поле
        last_air["selected_aircons"] = [
            {
                "id": ac.id,
                "model_name": ac.model_name,
                "brand": ac.brand,
                "cooling_power_kw": ac.cooling_power_kw,
                "retail_price_byn": ac.retail_price_byn,
                "is_inverter": ac.is_inverter,
                "has_wifi": ac.has_wifi,
                "mount_type": ac.mount_type,
                "description": ac.description,  # Добавляем поле description
                "image_path": ac.image_path  # Добавляем поле image_path
            }
            for ac in selected_aircons
        ]
        
        # Обновляем данные в базе
        order.compose_order_data = json.dumps(compose_order_data, ensure_ascii=False)
        await db.commit()
        
        logger.info(f"Подбор кондиционеров для составного заказа {order_id} завершен. Подобрано {len(selected_aircons)} вариантов.")
        return {"result_text": result_text, "selected_count": len(selected_aircons)}
        
    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров для составного заказа: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/add_aircon_to_compose_order/")
async def add_aircon_to_compose_order(payload: dict, db: AsyncSession = Depends(get_session)):
    """
    Добавляет новый кондиционер к существующему составному заказу с новой структурой (airs).
    Также сохраняет подобранные кондиционеры для предыдущего элемента.
    """
    # Логируем только ключевую информацию вместо полного payload
    order_id = payload.get("id")
    logger.info(f"Получен запрос на добавление кондиционера к составному заказу ID: {order_id}")
    try:
        order_id = payload.get("id")
        new_aircon_order = payload.get("new_aircon_order", {})
        
        if not order_id:
            return {"success": False, "error": "ID составного заказа не указан"}
        
        # Получаем составной заказ
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"success": False, "error": "Составной заказ не найден"}
        
        # Обновляем данные заказа с новой структурой
        compose_order_data = json.loads(order.compose_order_data)
        rooms = compose_order_data.get("rooms", [])
        
        # В новой логике работаем с помещениями, а не с отдельными кондиционерами
        # Этот эндпоинт может быть не нужен в новой логике, но оставляем для совместимости
        if rooms:
            room = rooms[0]
            selected_aircons = room.get("selected_aircons_for_room", [])
            if selected_aircons:
                logger.info(f"У помещения '{room.get('room_type', 'Помещение')}' уже есть подобранные кондиционеры")
        
        # В новой логике добавляем новое помещение вместо нового кондиционера
        new_room_id = len(rooms) + 1
        
        # Добавляем ID к данным кондиционера
        new_aircon_order["id"] = new_air_id
        
        # Добавляем в массив airs
        if "airs" not in compose_order_data:
            compose_order_data["airs"] = []
        compose_order_data["airs"].append(new_aircon_order)
        
        order.compose_order_data = json.dumps(compose_order_data, ensure_ascii=False)
        await db.commit()
        
        aircon_count = len(compose_order_data["airs"])
        logger.info(f"К составному заказу {order_id} добавлен кондиционер #{aircon_count} с ID {new_air_id}")
        return {"success": True, "aircon_count": aircon_count}
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении кондиционера к составному заказу: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/generate_compose_offer/")
async def generate_compose_offer(payload: dict, db: AsyncSession = Depends(get_session)):
    """
    Генерирует PDF коммерческое предложение для составного заказа.
    """
    # Логируем только ключевую информацию вместо полного payload
    order_id = payload.get("id")
    logger.info(f"Получен запрос на генерацию КП для составного заказа ID: {order_id}")
    try:
        order_id = payload.get("id")
        if not order_id:
            return {"success": False, "error": "ID составного заказа не указан"}
        
        # Получаем составной заказ
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"success": False, "error": "Составной заказ не найден"}
        
        compose_order_data = json.loads(order.compose_order_data)
        
        # Импортируем функцию генерации PDF
        from utils.compose_pdf_generator import generate_compose_commercial_offer_pdf
        
        # Проверяем, что есть помещения с подобранными кондиционерами
        rooms = compose_order_data.get("rooms", [])
        if not rooms:
            return {"success": False, "error": "В составном заказе нет данных о помещениях"}
        
        # Формируем структуру aircon_results из данных помещений
        aircon_results = {
            "aircon_results": []
        }
        
        rooms_with_selections = []
        for i, room in enumerate(rooms):
            selected_aircons = room.get("selected_aircons_for_room", [])
            logger.info(f"Помещение {i+1}: selected_aircons_for_room = {selected_aircons}")
            
            # Пропускаем базовую конфигурацию (rooms[0] без данных)
            if i == 0:
                room_type = room.get("room_type", "").strip()
                has_components = bool(room.get("components_for_room"))
                # Если это rooms[0] без названия или с дефолтным типом и нет кондиционеров/комплектующих - пропускаем
                if (not room_type or room_type == "квартира") and not selected_aircons and not has_components:
                    logger.info(f"Пропускаем базовую конфигурацию (rooms[0]) без данных")
                    continue
            
            # Проверяем, что selected_aircons это список, а не строка
            if isinstance(selected_aircons, str):
                logger.error(f"selected_aircons_for_room содержит строку вместо списка: {selected_aircons}")
                try:
                    selected_aircons = json.loads(selected_aircons)
                    logger.info(f"Успешно распарсили JSON: {len(selected_aircons)} кондиционеров")
                except:
                    logger.error("Не удалось распарсить selected_aircons как JSON")
                    selected_aircons = []
            
            logger.info(f"Помещение {i+1}: итого кондиционеров для обработки: {len(selected_aircons)}")
            if selected_aircons and isinstance(selected_aircons, list):
                # Формируем aircon_params из данных помещения
                aircon_params = {
                    "area": room.get("area", 0),
                    "brand": room.get("brand", "Любой"),
                    "wifi": room.get("wifi", False),
                    "inverter": room.get("inverter", False),
                    "price_limit": room.get("price_limit", 10000),
                    "mount_type": room.get("mount_type", "Любой"),
                    "ceiling_height": room.get("ceiling_height", 2.7),
                    "illumination": room.get("illumination", "Средняя"),
                    "num_people": room.get("num_people", 1),
                    "activity": room.get("activity", "Сидячая работа"),
                    "num_computers": room.get("num_computers", 0),
                    "num_tvs": room.get("num_tvs", 0),
                    "other_power": room.get("other_power", 0)
                }
                
                # Формируем order_params из данных помещения
                order_params = {
                    "room_type": room.get("room_type", "Помещение"),
                    "installation_price": room.get("installation_price", 0)
                }
                
                aircon_results["aircon_results"].append({
                    "aircon_params": aircon_params,
                    "order_params": order_params,
                    "selected_aircons": selected_aircons
                })
                rooms_with_selections.append(room)
        
        if not aircon_results["aircon_results"]:
            return {"success": False, "error": "Нет помещений с подобранными кондиционерами. Сначала подберите кондиционеры для всех помещений."}
        
        # Получаем скидку из данных клиента
        client_data = compose_order_data.get("client_data", {})
        discount_percent = client_data.get("discount", 0)
        
        # Собираем все комплектующие из всех помещений для общей сводки (исключая пустую базовую конфигурацию)
        rooms = compose_order_data.get("rooms", [])
        components = []
        for i, room in enumerate(rooms):
            # Пропускаем базовую конфигурацию (rooms[0] без данных)
            if i == 0:
                room_type = room.get("room_type", "").strip()
                selected_aircons = room.get("selected_aircons_for_room", [])
                has_components = bool(room.get("components_for_room"))
                # Если это rooms[0] без названия или с дефолтным типом и нет кондиционеров/комплектующих - пропускаем
                if (not room_type or room_type == "квартира") and not selected_aircons and not has_components:
                    logger.info(f"Пропускаем комплектующие из базовой конфигурации (rooms[0]) без данных")
                    continue
            
            room_components = room.get("components_for_room", [])
            if room_components:
                components.extend(room_components)
        
        # Генерируем PDF
        pdf_path = await generate_compose_commercial_offer_pdf(
            compose_order_data=compose_order_data,
            aircon_results=aircon_results,
            components=components,
            discount_percent=discount_percent,
            db_session=db
        )
        
        # Обновляем статус заказа и путь к PDF
        order.status = "completed"
        order.pdf_path = pdf_path
        await db.commit()
        
        logger.info(f"КП для составного заказа {order_id} успешно сгенерировано: {pdf_path}")
        return {"success": True, "pdf_path": pdf_path}
        
    except Exception as e:
        logger.error(f"Ошибка при генерации КП для составного заказа: {e}", exc_info=True)
        return {"success": False, "error": str(e)}