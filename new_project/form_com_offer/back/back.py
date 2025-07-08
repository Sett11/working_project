from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import datetime

from db import models, schemas, crud
from db.database import get_db
from utils.mylogger import Logger
from selection import aircon_selector, materials_calculator
from utils import pdf_generator

logger = Logger("back", "logs/back.log")

app = FastAPI(title="API для автоматизации продаж")

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI приложение запускается")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI приложение останавливается")


@app.post("/generate_commercial_offer/", response_model=schemas.Order)
def generate_commercial_offer(payload: schemas.CommercialOfferPayload, db: Session = Depends(get_db)):
    """
    Основной эндпоинт для создания коммерческого предложения.
    1. Находит или создает клиента.
    2. Создает заказ.
    3. Подбирает оборудование (пока заглушка).
    4. Генерирует PDF (пока заглушка).
    5. Возвращает созданный заказ.
    """
    logger.info(f"Получен запрос на создание КП для клиента: {payload.client_data.full_name}")

    try:
        # 1. Найти или создать клиента
        client = crud.get_client_by_phone(db, phone=payload.client_data.phone)
        if not client:
            client = crud.create_client(db, client=payload.client_data)
        
        # 2. Создать заказ
        order_create_schema = schemas.OrderCreate(
            client_id=client.id,
            manager_id=1, # ВРЕМЕННАЯ ЗАГЛУШКА: нужен ID текущего пользователя
            created_at=datetime.date.today(),
            room_type=payload.order_params.get("type_room"),
            room_area=payload.order_params.get("area"),
            discount=payload.order_params.get("discount", 0)
        )
        order = crud.create_order(db, order=order_create_schema)

        # 3. Подобрать оборудование (логика из selection)
        # TODO: Реализовать полноценный подбор
        # selected_aircons = aircon_selector.select_aircons(db, payload.aircon_params)
        # selected_components = materials_calculator.calculate_materials(order)
        logger.warning("Логика подбора оборудования и расчета материалов еще не реализована (заглушка).")

        # 4. Сгенерировать PDF
        # TODO: Реализовать генерацию PDF
        # pdf_path = pdf_generator.create_kp_pdf(order, selected_aircons, selected_components)
        # order.pdf_path = pdf_path
        # db.commit()
        logger.warning("Логика генерации PDF еще не реализована (заглушка).")

        logger.info(f"Заказ {order.id} для клиента {client.full_name} успешно создан.")
        
        # Возвращаем полный объект заказа
        return order

    except Exception as e:
        logger.error(f"Ошибка при создании коммерческого предложения: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при создании КП")


@app.get("/components/", response_model=List[schemas.Component])
def read_components(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Получает список всех комплектующих из базы данных.
    """
    logger.info(f"Запрос на получение списка комплектующих: skip={skip}, limit={limit}")
    try:
        components = crud.get_components(db, skip=skip, limit=limit)
        logger.info(f"Успешно получено {len(components)} комплектующих")
        return components
    except Exception as e:
        logger.error(f"Ошибка при получении комплектующих: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка сервера при получении комплектующих")

@app.get("/airconditioners/", response_model=List[schemas.AirConditioner])
def read_airconditioners(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Получает список всех кондиционеров из базы данных.
    """
    logger.info(f"Запрос на получение списка кондиционеров: skip={skip}, limit={limit}")
    try:
        airconditioners = crud.get_air_conditioners(db, skip=skip, limit=limit)
        logger.info(f"Успешно получено {len(airconditioners)} кондиционеров")
        return airconditioners
    except Exception as e:
        logger.error(f"Ошибка при получении кондиционеров: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка сервера при получении кондиционеров")