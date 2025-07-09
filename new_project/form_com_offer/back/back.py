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
def generate_offer_endpoint(payload: dict):
    """
    Эндпоинт для генерации коммерческого предложения.
    ПОКА ЧТО ЯВЛЯЕТСЯ ЗАГЛУШКОЙ.
    """
    logger.info("Получен запрос на эндпоинт /api/generate_offer/")
    logger.debug(f"Содержимое запроса: {payload}")

    # Здесь будет основная бизнес-логика:
    # 1. Создание/поиск клиента в БД (crud.get_or_create_client)
    # 2. Подбор кондиционеров по параметрам (selection.select_air_conditioner)
    # 3. Расчет комплектующих (selection.materials_calculator)
    # 4. Создание заказа в БД (crud.create_order)
    # 5. Генерация PDF (utils.pdf_generator)
    # 6. Сохранение PDF и привязка к заказу

    logger.warning("Используется временная заглушка! Бизнес-логика не реализована.")
    
    # Возвращаем заглушечный ответ
    response_data = {
        "aircons_list": "Список кондиционеров из заглушки бэкенда.",
        "pdf_path": None # Путь к сгенерированному PDF-файлу
    }
    
    return response_data
