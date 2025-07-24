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
import json

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
    logger.info(f"Получен запрос на эндпоинт /api/select_aircons/. Payload: {json.dumps(payload, ensure_ascii=False)}")
    try:
        # Если в payload только id — достаём параметры из заказа
        if list(payload.keys()) == ["id"] or ("id" in payload and len(payload) == 1):
            order_id = payload["id"]
            order = db.query(crud.models.Order).filter_by(id=order_id).first()
            if not order:
                logger.error(f"Заказ с id={order_id} не найден для подбора кондиционеров!")
                return {"error": f"Заказ с id={order_id} не найден!"}
            order_data = json.loads(order.order_data)
            aircon_params = order_data.get("aircon_params", {})
        else:
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
    logger.info(f"Получен запрос на эндпоинт /api/generate_offer/. Payload: {json.dumps(payload, ensure_ascii=False)}")
    try:
        # Если в payload только id — подгружаем все данные заказа из базы
        if list(payload.keys()) == ["id"] or ("id" in payload and len(payload) == 1):
            order_id = payload["id"]
            order = db.query(crud.models.Order).filter_by(id=order_id).first()
            if not order:
                logger.error(f"Заказ с id={order_id} не найден для генерации КП!")
                return {"error": f"Заказ с id={order_id} не найден!"}
            order_data = json.loads(order.order_data)
            client_data = order_data.get("client_data", {})
            order_params = order_data.get("order_params", {})
            aircon_params = order_data.get("aircon_params", {})
            components = order_data.get("components", [])
        else:
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
        # --- Формируем варианты для PDF ---
        aircon_variants = []
        variant_items = []
        for ac in selected_aircons:
            ac_dict = schemas.AirConditioner.from_orm(ac).dict()
            specs = []
            if ac_dict.get('cooling_power_kw'): specs.append(f"Охлаждение: {ac_dict['cooling_power_kw']} кВт")
            if ac_dict.get('heating_power_kw'): specs.append(f"Обогрев: {ac_dict['heating_power_kw']} кВт")
            if ac_dict.get('energy_efficiency_class'): specs.append(f"Класс: {ac_dict['energy_efficiency_class']}")
            if ac_dict.get('is_inverter'): specs.append("Инверторный")
            if ac_dict.get('has_wifi'): specs.append("Wi-Fi")
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
        today = datetime.date.today().strftime('%d_%m')
        # 2. Имя клиента для offer_number: только запрещённые для имени файла символы заменяем на '_', буквы и пробелы оставляем
        import re
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', client_full_name).strip()[:20]
        offer_number = f"{today}_{safe_name}"
        # 4. Генерируем PDF
        pdf_path = generate_commercial_offer_pdf(
            client_data=client_data, order_params=order_params,
            aircon_variants=aircon_variants, components=components_for_pdf,
            discount_percent=discount, offer_number=offer_number
        )
        # --- Меняем статус заказа на completed, если заказ найден по id ---
        if 'order' in locals() and order is not None:
            order.status = 'completed'
            order.pdf_path = pdf_path
            db.commit()
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
def save_order_endpoint(payload: dict, db: Session = Depends(get_session)):
    logger.info(f"Получен запрос на эндпоинт /api/save_order/ (сохранение/обновление заказа). Payload: {json.dumps(payload, ensure_ascii=False)}")
    try:
        # Определяем режим: только КП, только components, или оба
        has_kp = 'client_data' in payload and 'order_params' in payload and 'aircon_params' in payload
        has_components = 'components' in payload
        logger.info(f"Режим сохранения: КП={has_kp}, components={has_components}")
        # 1. Найти или создать клиента (если есть client_data)
        client = None
        if has_kp:
            client_data = payload["client_data"]
            client = crud.get_client_by_phone(db, client_data["phone"])
            if not client:
                client = crud.create_client(db, schemas.ClientCreate(**client_data))
        # 2. Получить существующий заказ, если есть id
        order_id = payload.get("id")
        order = None
        if order_id is not None:
            order = db.query(crud.models.Order).filter_by(id=order_id).first()
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
            order = crud.create_order(db, order_payload)
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
            db.commit()
            logger.info(f"Обновлён заказ id={order.id}. Итоговое order_data: {order.order_data}")
            return {"success": True, "order_id": order.id, "updated": True}
        logger.error("Не удалось найти или создать заказ для обновления.")
        return {"success": False, "error": "Не удалось найти или создать заказ."}
    except Exception as e:
        logger.error(f"Ошибка при сохранении/обновлении заказа: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера при обработке заказа: {e}")

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
        result = []
        for order in orders:
            result.append({
                "id": order.id,
                "client_name": json.loads(order.order_data)["client_data"]["full_name"],
                "created_at": order.created_at.strftime("%Y-%m-%d"),
                "status": order.status
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
        # Возвращаем order_data как есть (словарь)
        order_data = json.loads(order.order_data)
        order_data["id"] = order.id
        order_data["status"] = order.status
        order_data["pdf_path"] = order.pdf_path
        order_data["created_at"] = order.created_at.strftime("%Y-%m-%d")
        return order_data
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