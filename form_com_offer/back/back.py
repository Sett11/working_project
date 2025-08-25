"""
Основной файл бэкенда, реализующий API на FastAPI.
"""
from fastapi import FastAPI, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import datetime
import re
from db import crud, schemas
from db.database import get_session, AsyncSessionLocal, engine
from utils.mylogger import Logger
from utils.aircon_selector import select_aircons
from utils.pdf_generator import generate_commercial_offer_pdf_async
from db.schemas import FullOrderCreate
import json
from sqlalchemy import select
import threading
import time

logger = Logger(name=__name__, log_file="backend.log")
app = FastAPI(title="Air-Con Commercial Offer API", version="0.1.0")

# Глобальный обработчик исключений
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Необработанное исключение: {exc}", exc_info=True)
    return {"error": "Внутренняя ошибка сервера", "detail": str(exc)}

# ... (эндпоинты startup, shutdown, read_root, get_all_air_conditioners, select_aircons_endpoint без изменений) ...
@app.on_event("startup")
async def startup_event():
    logger.info("Запуск FastAPI приложения...")
    
    # Запускаем мониторинг пула соединений в фоновом режиме
    def monitor_pool():
        while True:
            try:
                from db.database import engine
                pool = engine.pool
                logger.info(f"Мониторинг пула: размер={pool.size()}, проверено={pool.checkedin()}, в использовании={pool.checkedout()}, переполнение={pool.overflow()}")
                time.sleep(300)  # Проверяем каждые 5 минут
            except Exception as e:
                logger.error(f"Ошибка мониторинга пула: {e}")
                time.sleep(60)  # При ошибке проверяем через минуту
    
    monitor_thread = threading.Thread(target=monitor_pool, daemon=True)
    monitor_thread.start()
    logger.info("Мониторинг пула соединений запущен")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Остановка FastAPI приложения.")

@app.get("/")
async def read_root():
    logger.info("Запрос к корневому эндпоинту '/' (проверка работоспособности API)")
    return {"message": "API бэкенда для подбора кондиционеров работает."}

@app.get("/health")
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
    logger.info(f"Получен запрос на эндпоинт /api/select_aircons/. Payload: {json.dumps(payload, ensure_ascii=False)}")
    try:
        # Если в payload только id — достаём параметры из заказа
        if list(payload.keys()) == ["id"] or ("id" in payload and len(payload) == 1):
            order_id = payload["id"]
            result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
            order = result.scalars().first()
            if not order:
                logger.error(f"Заказ с id={order_id} не найден для подбора кондиционеров!")
                return {"error": f"Заказ с id={order_id} не найден!"}
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
        selected_aircons = await select_aircons(db, aircon_params)
        logger.info(f"Подобрано {len(selected_aircons)} кондиционеров.")
        aircons_list = [schemas.AirConditioner.from_orm(ac).dict() for ac in selected_aircons]
        response_data = {"aircons_list": aircons_list, "total_count": len(selected_aircons)}
        logger.info("Подбор кондиционеров завершён успешно.")
        return response_data
    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при подборе кондиционеров: {e}")


# --- Эндпоинт для генерации КП (С УЛУЧШЕНИЕМ) ---
@app.post("/api/generate_offer/")
async def generate_offer_endpoint(payload: dict, db: AsyncSession = Depends(get_session)):
    logger.info(f"Получен запрос на эндпоинт /api/generate_offer/. Payload: {json.dumps(payload, ensure_ascii=False)}")
    try:
        # Если в payload только id — подгружаем все данные заказа из базы
        if list(payload.keys()) == ["id"] or ("id" in payload and len(payload) == 1):
            order_id = payload["id"]
            result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
            order = result.scalars().first()
            if not order:
                logger.error(f"Заказ с id={order_id} не найден для генерации КП!")
                return {"error": f"Заказ с id={order_id} не найден!"}
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
        
        selected_aircons = await select_aircons(db, aircon_params)
        # --- Формируем варианты для PDF ---
        aircon_variants = []
        variant_items = []
        for ac in selected_aircons:
            ac_dict = schemas.AirConditioner.from_orm(ac).dict()
            specs = []
            if ac_dict.get('cooling_power_kw'): specs.append(f"Охлаждение: {ac_dict['cooling_power_kw']} кВт")
            if ac_dict.get('energy_efficiency_class'): specs.append(f"Класс: {ac_dict['energy_efficiency_class']}")
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
                'short_description': ""
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
        # 4. Генерируем PDF
        pdf_path = await generate_commercial_offer_pdf_async(
            client_data=client_data, order_params=order_params,
            aircon_variants=aircon_variants, components=components_for_pdf,
            discount_percent=discount, offer_number=offer_number, db_session=db
        )
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
    logger.info(f"Получен запрос на эндпоинт /api/save_order/ (сохранение/обновление заказа). Payload: {json.dumps(payload, ensure_ascii=False)}")
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
        return {"error": str(e)}

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
                "comment": ""  # У составных заказов пока нет комментариев
            })
        logger.info(f"Отправлен список составных заказов: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении списка составных заказов: {e}", exc_info=True)
        return {"error": str(e)}

# --- Эндпоинт: получить объединенный список всех заказов ---
@app.get("/api/all_orders/")
async def get_all_orders_list(db: AsyncSession = Depends(get_session)):
    """
    Возвращает объединенный список всех заказов (обычных и составных) для фронта.
    """
    try:
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
        return all_orders
    except Exception as e:
        logger.error(f"Ошибка при получении объединенного списка заказов: {e}", exc_info=True)
        return {"error": str(e)}

# --- Эндпоинт: получить заказ по ID ---
@app.get("/api/order/{order_id}")
async def get_order_by_id(order_id: int = Path(...), db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"error": "Заказ не найден"}
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
        return {"error": str(e)}

# --- Эндпоинт: получить составной заказ по ID ---
@app.get("/api/compose_order/{order_id}")
async def get_compose_order_by_id(order_id: int = Path(...), db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"error": "Составной заказ не найден"}
        # Возвращаем compose_order_data как есть (словарь)
        compose_order_data = json.loads(order.compose_order_data)
        compose_order_data["id"] = order.id
        compose_order_data["status"] = order.status
        compose_order_data["pdf_path"] = order.pdf_path
        compose_order_data["created_at"] = order.created_at.strftime("%Y-%m-%d")
        return compose_order_data
    except Exception as e:
        logger.error(f"Ошибка при получении составного заказа по id: {e}", exc_info=True)
        return {"error": str(e)}

# --- Эндпоинт: удалить заказ по ID ---
@app.delete("/api/order/{order_id}")
async def delete_order(order_id: int = Path(...), db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(crud.models.Order).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"error": "Заказ не найден"}
        await db.delete(order)
        await db.commit()
        logger.info(f"Заказ id={order_id} успешно удалён")
        return {"success": True}
    except Exception as e:
        logger.error(f"Ошибка при удалении заказа: {e}", exc_info=True)
        return {"error": str(e)}

@app.delete("/api/compose_order/{order_id}")
async def delete_compose_order(order_id: int = Path(...), db: AsyncSession = Depends(get_session)):
    """Удаляет составной заказ по ID"""
    try:
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"error": "Составной заказ не найден"}
        await db.delete(order)
        await db.commit()
        logger.info(f"Составной заказ id={order_id} успешно удалён")
        return {"success": True}
    except Exception as e:
        logger.error(f"Ошибка при удалении составного заказа: {e}", exc_info=True)
        return {"error": str(e)}

# --- Эндпоинты для составных заказов ---

@app.post("/api/save_compose_order/")
async def save_compose_order(payload: dict, db: AsyncSession = Depends(get_session)):
    """
    Сохраняет или обновляет составной заказ с новой структурой данных (airs + components).
    """
    logger.info(f"Получен запрос на сохранение составного заказа: {json.dumps(payload, ensure_ascii=False)}")
    try:
        compose_order_data = payload.get("compose_order_data", {})
        logger.info(f"compose_order_data: {json.dumps(compose_order_data, ensure_ascii=False, indent=2)}")
        client_data = compose_order_data.get("client_data", {})
        
        # Проверяем, есть ли обновление комплектующих
        components_update = payload.get("components")
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
                # Обновляем только комплектующие
                existing_data = json.loads(order.compose_order_data)
                existing_data["components"] = components_update
                if status_update:
                    existing_data["status"] = status_update
                if comment_update is not None:
                    existing_data["comment"] = comment_update
                order.compose_order_data = json.dumps(existing_data, ensure_ascii=False)
                order.status = status_update or order.status
                logger.info(f"Обновлены комплектующие составного заказа id={order.id}")
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
                    logger.info(f"[DEBUG] Обновление последнего кондиционера: order_params из payload: {json.dumps(order_params, ensure_ascii=False)}")
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
                    logger.info(f"[DEBUG] Обновление последнего кондиционера: aircon_params из payload: {json.dumps(aircon_params, ensure_ascii=False)}")
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
                    
                    logger.info(f"[DEBUG] Обновление последнего кондиционера: safe_order_params: {json.dumps(safe_order_params, ensure_ascii=False)}")
                    logger.info(f"[DEBUG] Обновление последнего кондиционера: safe_aircon_params: {json.dumps(safe_aircon_params, ensure_ascii=False)}")
                    
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
    logger.info(f"Получен запрос на подбор кондиционеров для составного заказа: {json.dumps(payload, ensure_ascii=False)}")
    try:
        order_id = payload.get("id")
        if not order_id:
            return {"error": "ID составного заказа не указан"}
        
        # Получаем составной заказ
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"error": "Составной заказ не найден"}
        
        compose_order_data = json.loads(order.compose_order_data)
        airs = compose_order_data.get("airs", [])
        
        if not airs:
            return {"error": "В составном заказе нет кондиционеров для подбора"}
        
        # Берем последний добавленный кондиционер
        last_air = airs[-1]
        logger.info(f"Подбираем кондиционеры для последнего элемента с ID {last_air.get('id')}")
        
        # Импортируем функцию подбора для одного кондиционера
        from utils.compose_aircon_selector import select_aircons_for_params
        
        # Подбираем кондиционеры для последнего элемента
        aircon_params = last_air.get("aircon_params", {})
        order_params = last_air.get("order_params", {})
        
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
        from utils.aircon_selector import calculate_required_power
        
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
            result_text += f"   Тип монтажа: {ac.mount_type}\n\n"
        
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
                "description": ac.description  # Добавляем поле description
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
        return {"error": str(e)}

@app.post("/api/add_aircon_to_compose_order/")
async def add_aircon_to_compose_order(payload: dict, db: AsyncSession = Depends(get_session)):
    """
    Добавляет новый кондиционер к существующему составному заказу с новой структурой (airs).
    Также сохраняет подобранные кондиционеры для предыдущего элемента.
    """
    logger.info(f"Получен запрос на добавление кондиционера к составному заказу: {json.dumps(payload, ensure_ascii=False)}")
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
        airs = compose_order_data.get("airs", [])
        
        # Если есть предыдущий кондиционер, проверяем что у него есть подобранные кондиционеры
        if airs:
            last_air = airs[-1]
            if "selected_aircons" in last_air and last_air.get("selected_aircons"):
                logger.info(f"У элемента с ID {last_air.get('id')} уже есть подобранные кондиционеры")
        
        # Генерируем автоинкрементный ID для нового кондиционера
        new_air_id = len(airs) + 1
        
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
    logger.info(f"Получен запрос на генерацию КП для составного заказа: {json.dumps(payload, ensure_ascii=False)}")
    try:
        order_id = payload.get("id")
        if not order_id:
            return {"error": "ID составного заказа не указан"}
        
        # Получаем составной заказ
        result = await db.execute(select(crud.models.ComposeOrder).filter_by(id=order_id))
        order = result.scalars().first()
        if not order:
            return {"error": "Составной заказ не найден"}
        
        compose_order_data = json.loads(order.compose_order_data)
        
        # Импортируем функцию генерации PDF
        from utils.compose_pdf_generator import generate_compose_commercial_offer_pdf
        
        # Проверяем, что есть кондиционеры с подобранными вариантами
        airs = compose_order_data.get("airs", [])
        if not airs:
            return {"error": "В составном заказе нет кондиционеров"}
        
        # Формируем структуру aircon_results только для кондиционеров с подобранными вариантами
        aircon_results = {
            "aircon_results": []
        }
        
        airs_with_selections = []
        for air in airs:
            if "selected_aircons" in air and air.get("selected_aircons"):
                aircon_results["aircon_results"].append({
                    "aircon_params": air.get("aircon_params", {}),
                    "order_params": air.get("order_params", {}),
                    "selected_aircons": air.get("selected_aircons", [])
                })
                airs_with_selections.append(air)
        
        if not aircon_results["aircon_results"]:
            return {"error": "Нет кондиционеров с подобранными вариантами. Сначала подберите кондиционеры для всех помещений."}
        
        # Получаем скидку из первого кондиционера с подобранными вариантами
        discount_percent = airs_with_selections[0].get("order_params", {}).get("discount", 0) if airs_with_selections else 0
        
        # Генерируем PDF
        pdf_path = await generate_compose_commercial_offer_pdf(
            compose_order_data=compose_order_data,
            aircon_results=aircon_results,
            components=compose_order_data.get("components", []),
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
        return {"error": str(e)}