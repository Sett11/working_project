import json
from sqlalchemy.orm import Session
from . import models, schemas
from .database import SessionLocal, engine
from utils.mylogger import Logger

logger = Logger(name=__name__, log_file="db.log")

# Создаем все таблицы (на всякий случай, если еще не созданы)
logger.info("Проверка и создание таблиц в базе данных...")
try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Проверка и создание таблиц завершены.")
except Exception as e:
    logger.error(f"Ошибка при создании таблиц: {e}", exc_info=True)
    # Выход, если таблицы не могут быть созданы
    exit()


def seed_data():
    """
    Заполняет базу данных начальными данными из JSON-файлов.
    """
    db: Session = SessionLocal()
    
    try:
        # Проверяем, есть ли уже данные, чтобы не дублировать
        if db.query(models.AirConditioner).first() or db.query(models.Component).first():
            logger.info("База данных уже содержит данные. Наполнение не требуется.")
            return

        logger.info("Начинается процесс наполнения базы данных...")

        # 1. Наполнение таблицы кондиционеров
        logger.info("Загрузка данных из 'docs/airs_catalog.json'...")
        with open('docs/airs_catalog.json', 'r', encoding='utf-8') as f:
            airs_data = json.load(f)
        
        air_conditioners_to_add = airs_data.get("air_conditioners", [])
        for air_con_data in air_conditioners_to_add:
            # Создаем объект Pydantic для валидации
            air_con_schema = schemas.AirConditionerCreate(
                model_name=air_con_data.get("model_name"),
                brand=air_con_data.get("brand"),
                series=air_con_data.get("series"),
                cooling_power_kw=air_con_data.get("specifications", {}).get("cooling_power_kw"),
                heating_power_kw=air_con_data.get("specifications", {}).get("heating_power_kw"),
                pipe_diameter=air_con_data.get("specifications", {}).get("pipe_diameter"),
                energy_efficiency_class=air_con_data.get("specifications", {}).get("energy_efficiency_class"),
                retail_price_byn=air_con_data.get("pricing", {}).get("retail_price_byn"),
                description=air_con_data.get("description"),
                air_description=air_con_data.get("air_description"),
                representative_image=air_con_data.get("representative_image")
            )
            # Создаем объект модели SQLAlchemy
            db_air_con = models.AirConditioner(**air_con_schema.model_dump())
            db.add(db_air_con)
        
        db.commit()
        logger.info(f"Добавлено {len(air_conditioners_to_add)} кондиционеров.")

        # 2. Наполнение таблицы комплектующих
        logger.info("Загрузка данных из 'docs/components_catalog.json'...")
        with open('docs/components_catalog.json', 'r', encoding='utf-8') as f:
            components_data = json.load(f)

        components_to_add = components_data.get("components", [])
        for comp_data in components_to_add:
            comp_schema = schemas.ComponentCreate(**comp_data)
            db_comp = models.Component(**comp_schema.model_dump())
            db.add(db_comp)
            
        db.commit()
        logger.info(f"Добавлено {len(components_to_add)} комплектующих.")

        logger.info("Наполнение базы данных успешно завершено.")

    except Exception as e:
        logger.error(f"Произошла ошибка во время наполнения БД: {e}", exc_info=True)
        db.rollback()
    finally:
        logger.debug("Закрытие сессии базы данных.")
        db.close()

if __name__ == "__main__":
    seed_data()
