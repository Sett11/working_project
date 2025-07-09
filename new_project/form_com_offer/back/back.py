from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List

# Импортируем наши модули
from db import crud, schemas
from db.database import get_session
from utils.mylogger import Logger

# Инициализация логгера и FastAPI
logger = Logger(name=__name__, log_file="backend.log")
app = FastAPI(title="Air-Con Commercial Offer API", version="0.1.0")

@app.on_event("startup")
def startup_event():
    logger.info("Запуск FastAPI приложения...")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Остановка FastAPI приложения.")

# --- Тестовый эндпоинт ---
@app.get("/")
def read_root():
    """Корневой эндпоинт для проверки работы сервера."""
    logger.info("Запрос к корневому эндпоинту /")
    return {"message": "API бэкенда для подбора кондиционеров работает."}

# --- Эндпоинты для кондиционеров ---
@app.get("/api/air_conditioners/", response_model=List[schemas.AirConditioner])
def get_all_air_conditioners(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    """
    Получение списка всех кондиционеров из базы данных.
    """
    logger.info(f"Запрос на получение списка кондиционеров (skip={skip}, limit={limit}).")
    air_conditioners = crud.get_air_conditioners(db, skip=skip, limit=limit)
    return air_conditioners

# --- Эндпоинт для генерации КП ---
@app.post("/api/generate_offer/")
def generate_offer_endpoint(payload: dict, db: Session = Depends(get_session)):
    """
    Эндпоинт для генерации коммерческого предложения.
    """
    logger.info("Получен запрос на эндпоинт /api/generate_offer/")
    logger.debug(f"Содержимое запроса: {payload}")

    try:
        # Извлекаем данные из payload
        client_data = payload.get("client_data", {})
        order_params = payload.get("order_params", {})
        aircon_params = payload.get("aircon_params", {})
        
        logger.info(f"Обработка запроса для клиента: {client_data.get('full_name', 'N/A')}")
        
        # 1. Создание/поиск клиента в БД
        client = crud.get_client_by_phone(db, client_data.get("phone", ""))
        if not client:
            client_create = schemas.ClientCreate(**client_data)
            client = crud.create_client(db, client_create)
            logger.info(f"Создан новый клиент: {client.full_name}")
        else:
            logger.info(f"Найден существующий клиент: {client.full_name}")
        
        # 2. Подбор кондиционеров по параметрам
        from selection.aircon_selector import select_aircons
        selected_aircons = select_aircons(db, aircon_params)
        
        logger.info(f"Подобрано {len(selected_aircons)} кондиционеров")
        
        # 3. Формируем список кондиционеров для ответа
        aircons_list = []
        for aircon in selected_aircons:
            aircon_info = {
                "model_name": aircon.model_name,
                "brand": aircon.brand,
                "cooling_power_kw": aircon.cooling_power_kw,
                "heating_power_kw": aircon.heating_power_kw,
                "retail_price_byn": aircon.retail_price_byn,
                "is_inverter": aircon.is_inverter,
                "has_wifi": aircon.has_wifi,
                "mount_type": aircon.mount_type,
                "description": aircon.description
            }
            aircons_list.append(aircon_info)
        
        # 4. Формируем ответ
        response_data = {
            "aircons_list": aircons_list,
            "total_count": len(selected_aircons),
            "client_name": client.full_name,
            "pdf_path": None  # Пока без PDF
        }
        
        logger.info(f"КП успешно сформировано для клиента {client.full_name}")
        return response_data
        
    except Exception as e:
        logger.error(f"Ошибка при формировании КП: {str(e)}", exc_info=True)
        return {"error": f"Ошибка при формировании КП: {str(e)}"}

# --- Эндпоинт для подбора комплектующих ---
@app.post("/api/select_components/")
def select_components_endpoint(payload: dict, db: Session = Depends(get_session)):
    """
    Эндпоинт для подбора комплектующих по параметрам.
    """
    logger.info("Получен запрос на эндпоинт /api/select_components/")
    logger.debug(f"Содержимое запроса: {payload}")

    try:
        # Извлекаем параметры из payload
        category = payload.get("category")
        price_limit = payload.get("price_limit", 10000)
        
        logger.info(f"Подбор комплектующих: категория={category}, цена до {price_limit} BYN")
        
        # Формируем фильтр для запроса
        filters = {}
        if category and category != "Все категории":
            filters["category"] = category
        if price_limit:
            filters["price_limit"] = price_limit
        
        # Получаем комплектующие из БД
        components = crud.get_components_by_filters(db, filters)
        
        logger.info(f"Найдено {len(components)} подходящих комплектующих")
        
        # Формируем список комплектующих для ответа
        components_list = []
        for component in components:
            component_info = {
                "id": component.id,
                "name": component.name,
                "category": component.category,
                "size": component.size,
                "material": component.material,
                "characteristics": component.characteristics,
                "price": component.price,
                "currency": component.currency,
                "standard": component.standard,
                "manufacturer": component.manufacturer,
                "in_stock": component.in_stock,
                "description": component.description
            }
            components_list.append(component_info)
        
        # Формируем ответ
        response_data = {
            "components_list": components_list,
            "total_count": len(components),
            "category": category,
            "price_limit": price_limit
        }
        
        logger.info(f"Подбор комплектующих завершен успешно")
        return response_data
        
    except Exception as e:
        logger.error(f"Ошибка при подборе комплектующих: {str(e)}", exc_info=True)
        return {"error": f"Ошибка при подборе комплектующих: {str(e)}"}
