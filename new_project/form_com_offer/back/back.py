"""
Основной файл бэкенда, реализующий API на FastAPI.
"""
from fastapi import FastAPI, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
import datetime
import re
from db import crud, schemas
from db.database import get_session
from utils.mylogger import Logger
from selection.aircon_selector import select_aircons
from utils.pdf_generator import generate_commercial_offer_pdf
from db.schemas import FullOrderCreate

logger = Logger(name=__name__, log_file="backend.log")
app = FastAPI(title="Air-Con Commercial Offer API", version="0.1.0")

# ... (эндпоинты startup, shutdown, read_root, get_all_air_conditioners, select_aircons_endpoint без изменений) ...
@app.on_event("startup")
def startup_event():
    logger.info("Запуск FastAPI приложения...")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Остановка FastAPI приложения.")

@app.get("/")
def read_root():
    logger.info("Запрос к корневому эндпоинту '/' (проверка работоспособности API)")
    return {"message": "API бэкенда для подбора кондиционеров работает."}

@app.get("/api/air_conditioners/", response_model=List[schemas.AirConditioner])
def get_all_air_conditioners(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    logger.info(f"Запрос на получение списка кондиционеров (skip={skip}, limit={limit}).")
    try:
        air_conditioners = crud.get_air_conditioners(db, skip=skip, limit=limit)
        logger.info(f"Успешно получено {len(air_conditioners)} записей о кондиционерах.")
        return air_conditioners
    except Exception as e:
        logger.error(f"Ошибка при получении списка кондиционеров: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при получении данных.")

@app.post("/api/select_aircons/")
def select_aircons_endpoint(payload: dict, db: Session = Depends(get_session)):
    logger.info("Получен запрос на эндпоинт /api/select_aircons/")
    try:
        aircon_params = payload.get("aircon_params", {})
        client_full_name = payload.get("client_data", {}).get('full_name', 'N/A')
        logger.info(f"Начат подбор кондиционеров для клиента: {client_full_name}")
        selected_aircons = select_aircons(db, aircon_params)
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
def generate_offer_endpoint(payload: dict, db: Session = Depends(get_session)):
    logger.info("Получен запрос на эндпоинт /api/generate_offer/")
    
    try:
        client_data = payload.get("client_data", {})
        order_params = payload.get("order_params", {})
        aircon_params = payload.get("aircon_params", {})
        components = payload.get("components", [])
        discount = order_params.get("discount", 0)
        client_full_name = client_data.get('full_name', 'N/A')
        
        # 1. Создание или поиск клиента
        client_phone = client_data.get("phone")
        if not client_phone:
            raise HTTPException(status_code=400, detail="Отсутствует номер телефона клиента.")
        client = crud.get_client_by_phone(db, client_phone)
        if not client:
            client = crud.create_client(db, schemas.ClientCreate(**client_data))
        
        # 2. Подбор кондиционеров
        selected_aircons = select_aircons(db, aircon_params)
        
        # --- УЛУЧШЕНИЕ ЗДЕСЬ: Формируем более подробные варианты для PDF ---
        aircon_variants = []
        variant_items = []
        for ac in selected_aircons:
            ac_dict = schemas.AirConditioner.from_orm(ac).dict()
            
            # Формируем список характеристик
            specs = []
            if ac_dict.get('cooling_power_kw'): specs.append(f"Охлаждение: {ac_dict['cooling_power_kw']} кВт")
            if ac_dict.get('heating_power_kw'): specs.append(f"Обогрев: {ac_dict['heating_power_kw']} кВт")
            if ac_dict.get('energy_efficiency_class'): specs.append(f"Класс: {ac_dict['energy_efficiency_class']}")
            if ac_dict.get('is_inverter'): specs.append("Инверторный")
            if ac_dict.get('has_wifi'): specs.append("Wi-Fi")
            
            # Достаем 'features' из описания, если они там есть
            description = ac_dict.get('description', '')
            if "Особенности: " in description:
                features_str = description.split("Особенности: ")[-1]
                specs.extend([f.strip() for f in features_str.split(',')])

            variant_items.append({
                'name': f"{ac_dict.get('brand', '')} {ac_dict.get('model_name', '')}",
                'manufacturer': ac_dict.get('brand', ''),
                'price': ac_dict.get('retail_price_byn', 0),
                'qty': 1, 'unit': 'шт.', 'delivery': 'в наличии',
                'discount_percent': float(order_params.get('discount', 0)),
                'specifications': specs, # Передаем расширенный список характеристик
                'short_description': "" # Поле больше не используется
            })
        
        aircon_variants.append({
            'title': 'Варианты оборудования, подходящие по параметрам',
            'description': '', # Убираем старое описание
            'items': variant_items
        })
        # --- Конец улучшения ---

        components_for_pdf = []
        for comp in components:
            comp_new = comp.copy()
            comp_new.setdefault('unit', 'шт.')
            comp_new.setdefault('discount_percent', discount)
            components_for_pdf.append(comp_new)
            
        today = datetime.date.today().strftime('%d_%m')
        safe_name = re.sub(r'[^\w]', '_', client_full_name)[:20]
        offer_number = f"{today}_{safe_name}"

        # 4. Генерируем PDF
        pdf_path = generate_commercial_offer_pdf(
            client_data=client_data, order_params=order_params,
            aircon_variants=aircon_variants, components=components_for_pdf,
            discount_percent=discount, offer_number=offer_number
        )

        response_data = {
            "aircon_variants": aircon_variants, # Для отладки
            "total_count": len(selected_aircons),
            "client_name": client.full_name,
            "components": components_for_pdf, # Для отладки
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
def save_order_endpoint(payload: FullOrderCreate, db: Session = Depends(get_session)):
    logger.info("Получен запрос на эндпоинт /api/save_order/ (сохранение черновика заказа)")
    try:
        # 1. Клиент
        client_data = payload.client_data
        client = crud.get_client_by_phone(db, client_data.phone)
        if not client:
            client = crud.create_client(db, client_data)
        # 2. OrderCreate
        order_params = payload.order_params or {}
        # 3. Формируем OrderCreate
        from datetime import date
        order_create = schemas.OrderCreate(
            client_id=client.id,
            created_at=date.today(),
            visit_date=order_params.get("visit_date"),
            status=payload.status or "draft",
            discount=order_params.get("discount", 0),
            room_type=order_params.get("room_type"),
            room_area=order_params.get("room_area"),
            installer_data=None  # Можно добавить дополнительные данные, если нужно
        )
        order = crud.create_order(db, order_create)
        logger.info(f"Заказ-черновик успешно сохранён с id={order.id}")
        return {"success": True, "order_id": order.id}
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа: {e}", exc_info=True)
        return {"error": str(e)}

# --- Эндпоинт: получить список всех заказов (id, имя, дата, адрес, статус) ---
@app.get("/api/orders/")
def get_orders_list(db: Session = Depends(get_session)):
    """
    Возвращает список всех заказов для фронта.
    Сначала идут заказы в статусе 'draft' или 'forming' (редактируются), затем остальные.
    Внутри групп сортировка по дате создания (новые выше).
    Логирует результат и ошибки.
    """
    try:
        orders = db.query(crud.models.Order).all()
        logger.info(f"Всего заказов в базе: {len(orders)}")
        # Группируем по статусу
        editing_statuses = ("draft", "forming")
        editing_orders = [o for o in orders if o.status in editing_statuses]
        other_orders = [o for o in orders if o.status not in editing_statuses]
        # Сортируем внутри групп по дате создания (новые выше)
        editing_orders.sort(key=lambda o: o.created_at, reverse=True)
        other_orders.sort(key=lambda o: o.created_at, reverse=True)
        sorted_orders = editing_orders + other_orders
        result = []
        for order in sorted_orders:
            status = order.status
            if status in ("forming", "draft"): status_str = "Уточнение деталей"
            elif status == "generated": status_str = "Сформировано КП"
            else: status_str = status
            result.append({
                "id": order.id,
                "client_name": order.client.full_name if order.client else "-",
                "created_at": order.created_at.strftime("%Y-%m-%d"),
                "address": order.client.address if order.client else "-",
                "status": status_str
            })
        logger.info(f"Отправлен список заказов: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении списка заказов: {e}", exc_info=True)
        return {"error": str(e)}

# --- Эндпоинт: получить заказ по ID ---
@app.get("/api/order/{order_id}")
def get_order_by_id(order_id: int = Path(...), db: Session = Depends(get_session)):
    try:
        order = db.query(crud.models.Order).filter_by(id=order_id).first()
        if not order:
            return {"error": "Заказ не найден"}
        # Собираем все данные для автозаполнения (примерно как на фронте)
        client = order.client
        client_data = {
            "full_name": client.full_name if client else "",
            "phone": client.phone if client else "",
            "email": client.email if client else "",
            "address": client.address if client else ""
        }
        order_params = {
            "room_area": order.room_area,
            "room_type": order.room_type,
            "discount": order.discount,
            "visit_date": order.visit_date.strftime("%Y-%m-%d") if order.visit_date else None,
            "installation_price": None # если есть
        }
        # aircon_params и components — если нужно, можно доработать
        return {
            "id": order.id,
            "client_data": client_data,
            "order_params": order_params,
            "status": order.status
        }
    except Exception as e:
        logger.error(f"Ошибка при получении заказа по id: {e}", exc_info=True)
        return {"error": str(e)}

# --- Эндпоинт: удалить заказ по ID ---
@app.delete("/api/order/{order_id}")
def delete_order(order_id: int = Path(...), db: Session = Depends(get_session)):
    try:
        order = db.query(crud.models.Order).filter_by(id=order_id).first()
        if not order:
            return {"error": "Заказ не найден"}
        db.delete(order)
        db.commit()
        logger.info(f"Заказ id={order_id} успешно удалён")
        return {"success": True}
    except Exception as e:
        logger.error(f"Ошибка при удалении заказа: {e}", exc_info=True)
        return {"error": str(e)}