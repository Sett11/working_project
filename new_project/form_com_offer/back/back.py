"""
Основной файл бэкенда, реализующий API на FastAPI.

Этот модуль определяет эндпоинты для взаимодействия с базой данных,
подбора кондиционеров и генерации коммерческих предложений.
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# Импортируем наши модули
from db import crud, schemas
from db.database import get_session
from utils.mylogger import Logger
from selection.aircon_selector import select_aircons

# Инициализация логгера для бэкенда.
# log_file указывается без папки logs, чтобы использовать дефолтную директорию логов.
logger = Logger(name=__name__, log_file="backend.log")

# Инициализация приложения FastAPI с указанием названия и версии.
app = FastAPI(title="Air-Con Commercial Offer API", version="0.1.0")


@app.on_event("startup")
def startup_event():
    """
    Событие, выполняемое при старте приложения.
    Логирует запуск FastAPI-приложения.
    """
    logger.info("Запуск FastAPI приложения...")


@app.on_event("shutdown")
def shutdown_event():
    """
    Событие, выполняемое при остановке приложения.
    Логирует остановку FastAPI-приложения.
    """
    logger.info("Остановка FastAPI приложения.")


# --- Тестовый эндпоинт ---
@app.get("/")
def read_root():
    """
    Корневой эндпоинт для проверки работоспособности API.
    Возвращает приветственное сообщение.
    """
    logger.info("Запрос к корневому эндпоинту '/' (проверка работоспособности API)")
    return {"message": "API бэкенда для подбора кондиционеров работает."}


# --- Эндпоинты для кондиционеров ---
@app.get("/api/air_conditioners/", response_model=List[schemas.AirConditioner])
def get_all_air_conditioners(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    """
    Получение списка всех кондиционеров из базы данных с возможностью пагинации.

    Args:
        skip (int): Количество записей, которое нужно пропустить.
        limit (int): Максимальное количество записей для возврата.
        db (Session): Сессия базы данных.

    Returns:
        List[schemas.AirConditioner]: Список кондиционеров.
    """
    logger.info(f"Запрос на получение списка кондиционеров (skip={skip}, limit={limit}).")
    try:
        # Получаем кондиционеры с пагинацией через crud-слой
        air_conditioners = crud.get_air_conditioners(db, skip=skip, limit=limit)
        logger.info(f"Успешно получено {len(air_conditioners)} записей о кондиционерах.")
        return air_conditioners
    except Exception as e:
        logger.error(f"Ошибка при получении списка кондиционеров: {e}", exc_info=True)
        # В случае ошибки возвращаем HTTP-исключение.
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при получении данных.")


# --- Эндпоинт для подбора только кондиционеров ---
@app.post("/api/select_aircons/")
def select_aircons_endpoint(payload: dict, db: Session = Depends(get_session)):
    """
    Эндпоинт для подбора кондиционеров на основе переданных параметров.
    Не генерирует коммерческое предложение, только возвращает список подходящих моделей.

    Args:
        payload (dict): Словарь с параметрами для подбора.
        db (Session): Сессия базы данных.

    Returns:
        dict: Словарь со списком подобранных кондиционеров и их количеством.
    """
    logger.info("Получен запрос на эндпоинт /api/select_aircons/")
    logger.debug(f"Содержимое запроса: {payload}")

    try:
        # Извлекаем параметры из тела запроса.
        aircon_params = payload.get("aircon_params", {})
        client_full_name = payload.get("client_data", {}).get('full_name', 'N/A')
        
        logger.info(f"Начат подбор кондиционеров для клиента: {client_full_name}")
        
        # Вызываем функцию подбора кондиционеров.
        selected_aircons = select_aircons(db, aircon_params)
        
        logger.info(f"Подобрано {len(selected_aircons)} кондиционеров.")
        
        # Формируем список кондиционеров для ответа, используя схему Pydantic для валидации.
        aircons_list = [schemas.AirConditioner.from_orm(ac).dict() for ac in selected_aircons]
        
        # Формируем успешный ответ.
        response_data = {
            "aircons_list": aircons_list,
            "total_count": len(selected_aircons)
        }
        
        logger.info("Подбор кондиционеров завершён успешно.")
        return response_data
        
    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {e}", exc_info=True)
        # Возвращаем HTTP-исключение с деталями ошибки.
        raise HTTPException(status_code=500, detail=f"Ошибка при подборе кондиционеров: {e}")


# --- Эндпоинт для генерации КП ---
@app.post("/api/generate_offer/")
def generate_offer_endpoint(payload: dict, db: Session = Depends(get_session)):
    """
    Эндпоинт для полной обработки запроса: создание клиента, подбор кондиционеров
    и подготовка данных для коммерческого предложения.

    Args:
        payload (dict): Словарь с данными клиента, параметрами заказа и подбора.
        db (Session): Сессия базы данных.

    Returns:
        dict: Словарь с результатами, включая список кондиционеров и данные клиента.
    """
    logger.info("Получен запрос на эндпоинт /api/generate_offer/")
    logger.debug(f"Содержимое запроса: {payload}")

    try:
        # Извлекаем данные из тела запроса.
        client_data = payload.get("client_data", {})
        aircon_params = payload.get("aircon_params", {})
        components = payload.get("components", [])
        
        client_full_name = client_data.get('full_name', 'N/A')
        logger.info(f"Обработка запроса на генерацию КП для клиента: {client_full_name}")
        
        # 1. Создание или поиск клиента в БД.
        client_phone = client_data.get("phone")
        if not client_phone:
            logger.warning("В запросе отсутствует номер телефона клиента.")
            raise HTTPException(status_code=400, detail="Отсутствует номер телефона клиента.")

        client = crud.get_client_by_phone(db, client_phone)
        if not client:
            logger.info(f"Клиент с телефоном {client_phone} не найден. Создание нового клиента.")
            client_create = schemas.ClientCreate(**client_data)
            client = crud.create_client(db, client_create)
            logger.info(f"Создан новый клиент: {client.full_name} (ID: {client.id})")
        else:
            logger.info(f"Найден существующий клиент: {client.full_name} (ID: {client.id})")
        
        # 2. Подбор кондиционеров по параметрам.
        logger.info("Начат подбор кондиционеров...")
        selected_aircons = select_aircons(db, aircon_params)
        logger.info(f"Подобрано {len(selected_aircons)} кондиционеров.")
        
        # 3. Формируем список кондиционеров для ответа.
        aircons_list = [schemas.AirConditioner.from_orm(ac).dict() for ac in selected_aircons]
        
        # 4. Формируем успешный ответ.
        response_data = {
            "aircons_list": aircons_list,
            "total_count": len(selected_aircons),
            "client_name": client.full_name,
            "components": components,
            "pdf_path": None  # Генерация PDF на данном этапе не реализована.
        }
        
        logger.info(f"Данные для КП успешно сформированы для клиента {client.full_name}")
        return response_data
        
    except HTTPException as http_exc:
        # Перехватываем и пробрасываем HTTP исключения, чтобы FastAPI их обработал.
        raise http_exc
    except Exception as e:
        logger.error(f"Ошибка при формировании КП: {e}", exc_info=True)
        # В случае других ошибок возвращаем общее сообщение.
        raise HTTPException(status_code=500, detail=f"Ошибка при формировании КП: {e}")




