"""
Модуль для наполнения базы данных начальными данными из JSON-файлов.

Этот скрипт:
- Проверяет и создаёт таблицы в базе данных, если они ещё не созданы.
- Загружает данные кондиционеров и комплектующих из файлов docs/airs_catalog.json и docs/components_catalog.json.
- Добавляет их в базу данных, если она пуста.
- Поддерживает повторный запуск без дублирования данных.
"""
import json
from sqlalchemy.orm import Session
from db import models, schemas
from db.database import SessionLocal, engine
from utils.mylogger import Logger
import os

logger = Logger(name=__name__, log_file="db.log")

# Пути к каталогам
AIRS_CATALOG_PATH = 'docs/airs_catalog.json'
COMPONENTS_CATALOG_PATH = 'docs/components_catalog.json'

# Создаём все таблицы
logger.info("Проверка и создание таблиц в базе данных...")
try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Проверка и создание таблиц завершены.")
except Exception as e:
    logger.error(f"Ошибка при создании таблиц: {e}", exc_info=True)
    exit()


def seed_data():
    """
    Заполняет базу данных начальными данными из JSON-файлов.
    """
    db: Session = SessionLocal()
    
    try:
        # --- 1. Наполнение таблицы кондиционеров (логика без изменений) ---
        if not db.query(models.AirConditioner).first():
            logger.info("Начинается наполнение таблицы кондиционеров...")
            if not os.path.exists(AIRS_CATALOG_PATH):
                logger.warning(f"Файл {AIRS_CATALOG_PATH} не найден. Пропуск наполнения кондиционеров.")
            else:
                with open(AIRS_CATALOG_PATH, 'r', encoding='utf-8') as f:
                    airs_data = json.load(f)
                
                air_conditioners_to_add = airs_data.get("air_conditioners", [])
                for air_con_data in air_conditioners_to_add:
                    air_description = air_con_data.get("air_description", "").lower()
                    is_inverter = "инвертор" in air_description or "inverter" in air_description
                    has_wifi = "wi-fi" in air_description or "wifi" in air_description
                    mount_type = next((mt for mt in ["настенный", "кассетный", "потолочный", "напольный", "колонный"] if mt in air_description), None)

                    air_con_schema = schemas.AirConditionerCreate(
                        model_name=air_con_data.get("model_name"), brand=air_con_data.get("brand"),
                        series=air_con_data.get("series"),
                        cooling_power_kw=air_con_data.get("specifications", {}).get("cooling_power_kw"),
                        heating_power_kw=air_con_data.get("specifications", {}).get("heating_power_kw"),
                        pipe_diameter=air_con_data.get("specifications", {}).get("pipe_diameter"),
                        energy_efficiency_class=air_con_data.get("specifications", {}).get("energy_efficiency_class"),
                        retail_price_byn=air_con_data.get("pricing", {}).get("retail_price_byn"),
                        description=air_con_data.get("description"), air_description=air_con_data.get("air_description"),
                        representative_image=air_con_data.get("representative_image"),
                        is_inverter=is_inverter, has_wifi=has_wifi, mount_type=mount_type
                    )
                    db_air_con = models.AirConditioner(**air_con_schema.model_dump())
                    db.add(db_air_con)
                
                db.commit()
                logger.info(f"Добавлено {len(air_conditioners_to_add)} кондиционеров.")
        else:
            logger.info("Таблица кондиционеров уже содержит данные. Наполнение не требуется.")

        # --- 2. Наполнение таблицы комплектующих (ОБНОВЛЕННАЯ ЛОГИКА) ---
        if not db.query(models.Component).first():
            logger.info("Начинается наполнение таблицы комплектующих...")
            if not os.path.exists(COMPONENTS_CATALOG_PATH):
                logger.warning(f"Файл {COMPONENTS_CATALOG_PATH} не найден. Пропуск наполнения комплектующих.")
            else:
                with open(COMPONENTS_CATALOG_PATH, 'r', encoding='utf-8') as f:
                    components_data = json.load(f)

                # Получаем валюту из общей информации о каталоге
                global_currency = components_data.get("catalog_info", {}).get("currency", "BYN")
                
                components_to_add = components_data.get("components", [])
                for comp_data in components_to_add:
                    # Создаем схему, сопоставляя новые поля
                    comp_schema = schemas.ComponentCreate(
                        name=comp_data.get("name"),
                        category=comp_data.get("category"),
                        price=comp_data.get("price"),
                        size=comp_data.get("size"),
                        # Поля 'material' и 'standard' отсутствуют в новом JSON, будут None
                        material=comp_data.get("material"), 
                        characteristics=comp_data.get("characteristics"),
                        currency=global_currency, # Используем глобальную валюту
                        manufacturer=comp_data.get("manufacturer"),
                        in_stock=comp_data.get("in_stock", True),
                        description=comp_data.get("description"),
                        # Поле 'image_url' отсутствует
                        image_url=None 
                    )
                    db_comp = models.Component(**comp_schema.model_dump())
                    db.add(db_comp)
                
                db.commit()
                logger.info(f"Добавлено {len(components_to_add)} комплектующих.")
        else:
            logger.info("Таблица комплектующих уже содержит данные. Наполнение не требуется.")

        logger.info("Наполнение базы данных успешно завершено.")

    except Exception as e:
        logger.error(f"Произошла ошибка во время наполнения БД: {e}", exc_info=True)
        db.rollback()
    finally:
        logger.debug("Закрытие сессии базы данных.")
        db.close()

if __name__ == "__main__":
    seed_data()