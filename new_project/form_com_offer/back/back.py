"""
Основной файл бэкенда, реализующий API на FastAPI.
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import datetime
import re
from db import crud, schemas
from db.database import get_session
from utils.mylogger import Logger
from selection.aircon_selector import select_aircons
from utils.pdf_generator import generate_commercial_offer_pdf

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