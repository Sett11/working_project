"""
Модуль для наполнения базы данных начальными данными из JSON-файлов.
"""
import json
import re
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas
from .database import AsyncSessionLocal, engine, Base
from utils.mylogger import Logger
import os
from sqlalchemy import select, func, delete

logger = Logger(name=__name__, log_file="db.log")

AIRS_CATALOG_PATH = 'docs/airs_catalog.json'
COMPONENTS_CATALOG_PATH = 'docs/components_catalog.json'


async def create_tables():
    logger.info("Проверка и создание таблиц в базе данных (async)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Проверка и создание таблиц завершены.")

async def seed_data():
    await create_tables()
    """
    Заполняет базу данных начальными данными из JSON-файлов.
    """
    async with AsyncSessionLocal() as db:
        try:
            # --- 1. Наполнение таблицы кондиционеров (ОБНОВЛЕННАЯ ЛОГИКА) ---
            logger.info("Начинается наполнение таблицы кондиционеров...")
            if not os.path.exists(AIRS_CATALOG_PATH):
                logger.warning(f"Файл {AIRS_CATALOG_PATH} не найден. Пропуск.")
            else:
                # Очищаем таблицу перед заполнением
                stmt_count = select(func.count()).select_from(models.AirConditioner)
                result = await db.execute(stmt_count)
                existing_count = result.scalar()
                if existing_count > 0:
                    logger.info(f"Очистка существующих {existing_count} записей кондиционеров...")
                    await db.execute(delete(models.AirConditioner))
                    await db.commit()
                    logger.info("Таблица кондиционеров очищена.")
                
                with open(AIRS_CATALOG_PATH, 'r', encoding='utf-8') as f:
                    airs_data = json.load(f)
                
                air_conditioners_to_add = airs_data.get("air_conditioners", [])
                added_count = 0
                skipped_count = 0
                
                for air_con_data in air_conditioners_to_add:
                    
                    # --- ПРОВЕРКА ОБЯЗАТЕЛЬНЫХ ПОЛЕЙ ---
                    record_id = air_con_data.get("id", "Unknown")
                    model_name = air_con_data.get("model_name")
                    if not model_name:
                        logger.warning(f"Пропуск записи с ID {record_id}: отсутствует model_name")
                        skipped_count += 1
                        continue
                    
                    # --- ПРОВЕРКА ДУБЛИКАТОВ ---
                    # Проверка на дубликат model_name
                    stmt = select(models.AirConditioner).where(models.AirConditioner.model_name == model_name)
                    result = await db.execute(stmt)
                    existing_model = result.scalar()
                    if existing_model:
                        logger.warning(f"Пропуск записи с ID {record_id}: дубликат model_name {model_name}")
                        skipped_count += 1
                        continue
                    
                    # --- НОВАЯ ЛОГИКА ИЗВЛЕЧЕНИЯ ДАННЫХ ---
                    
                    specs = air_con_data.get("specifications", {})
                    pricing = air_con_data.get("pricing", {})
                    features = [f.lower() for f in specs.get("features", [])] # Приводим все фичи к нижнему регистру для удобства

                    # Определяем наличие инвертора и Wi-Fi по списку features
                    is_inverter = any("инвертор" in f for f in features)
                    has_wifi = any("wi-fi" in f or "wifi" in f for f in features)

                    # Определяем тип монтажа по полю type, если оно есть
                    mount_type_map = {
                        "Nastennyy": "настенный",
                        "Kassetnyy": "кассетный",
                        "Potolochnyy": "потолочный",
                        "Napolnyy": "напольный",
                        "Kolonnyy": "колонный"
                    }
                    mount_type = mount_type_map.get(air_con_data.get("type"))
                    
                    # Собираем класс энергоэффективности из двух полей в одну строку
                    eer = specs.get("energy_efficiency_eer_seer", "N/A")
                    cop = specs.get("energy_efficiency_cop_scop", "N/A")
                    energy_class = f"Охлаждение: {eer} / Обогрев: {cop}"
                    
                    # Собираем описание из ключевых характеристик
                    description_parts = [f"Бренд: {air_con_data.get('brand')}, Серия: {air_con_data.get('series')}"]
                    if features:
                        description_parts.append("Особенности: " + ", ".join(specs.get("features")))
                    
                    description = ". ".join(description_parts)

                    # --- ОБРАБОТКА ЦЕНЫ ---
                    retail_price_raw = pricing.get("retail_price_byn")
                    retail_price_byn = None
                    if retail_price_raw is not None:
                        if isinstance(retail_price_raw, (int, float)):
                            retail_price_byn = float(retail_price_raw)
                        elif isinstance(retail_price_raw, str):
                            # Пытаемся извлечь число из строки
                            price_match = re.search(r'\d+(?:\.\d+)?', retail_price_raw)
                            if price_match:
                                retail_price_byn = float(price_match.group())
                            else:
                                logger.warning(f"Запись с ID {record_id}: не удалось извлечь цену из '{retail_price_raw}'")
                        else:
                            logger.warning(f"Запись с ID {record_id}: неожиданный тип цены {type(retail_price_raw)}")

                    # Создаём Pydantic-схему для валидации
                    air_con_schema = schemas.AirConditionerCreate(
                        model_name=model_name,  # Используем проверенное значение
                        brand=air_con_data.get("brand"),
                        series=air_con_data.get("series"),
                        # Пути к спецификациям
                        cooling_power_kw=specs.get("cooling_power_kw"),
                        heating_power_kw=specs.get("heating_power_kw"),
                        pipe_diameter=specs.get("pipe_diameter_mm"), # Путь изменился
                        energy_efficiency_class=energy_class, # Используем собранную строку
                        # Пути к ценам
                        retail_price_byn=retail_price_byn,  # Используем обработанную цену
                        # Описание и картинка
                        description=description, # Используем новое собранное описание
                        air_description=None, # Старое поле больше не нужно
                        representative_image=air_con_data.get("representative_image"), # Путь остался прежним
                        # Новые, более надежные флаги
                        is_inverter=is_inverter,
                        has_wifi=has_wifi,
                        mount_type=mount_type
                    )
                    db_air_con = models.AirConditioner(**air_con_schema.model_dump())
                    db.add(db_air_con)
                    try:
                        await db.commit()
                    except Exception as commit_error:
                        logger.error(f"Ошибка при добавлении записи {model_name}: {commit_error}")
                        await db.rollback()
                        skipped_count += 1
                        continue
                    added_count += 1
                logger.info(f"Добавлено {added_count} кондиционеров, пропущено {skipped_count}.")

            # --- 2. Наполнение таблицы комплектующих ---
            logger.info("Начинается наполнение таблицы комплектующих...")
            stmt_count_comp = select(func.count()).select_from(models.Component)
            result = await db.execute(stmt_count_comp)
            existing_count = result.scalar()
            if existing_count == 0:
                if not os.path.exists(COMPONENTS_CATALOG_PATH):
                    logger.warning(f"Файл {COMPONENTS_CATALOG_PATH} не найден. Пропуск.")
                else:
                    with open(COMPONENTS_CATALOG_PATH, 'r', encoding='utf-8') as f:
                        components_data = json.load(f)
                    global_currency = components_data.get("catalog_info", {}).get("currency", "BYN")
                    components_to_add = components_data.get("components", [])
                    for comp_data in components_to_add:
                        comp_schema = schemas.ComponentCreate(
                            name=comp_data.get("name"), category=comp_data.get("category"),
                            price=comp_data.get("price"), size=comp_data.get("size"),
                            material=comp_data.get("material"), characteristics=comp_data.get("characteristics"),
                            currency=global_currency, manufacturer=comp_data.get("manufacturer"),
                            in_stock=comp_data.get("in_stock", True), description=comp_data.get("description"),
                            image_url=comp_data.get("image_path")
                        )
                        db_comp = models.Component(**comp_schema.model_dump())
                        db.add(db_comp)
                    await db.commit()
                    logger.info(f"Добавлено {len(components_to_add)} комплектующих.")
            else:
                logger.info("Таблица комплектующих уже содержит данные. Наполнение не требуется.")

        except Exception as e:
            logger.error(f"Произошла ошибка во время наполнения БД: {e}", exc_info=True)
            await db.rollback()
        finally:
            logger.debug("Закрытие сессии базы данных.")

if __name__ == "__main__":
    asyncio.run(seed_data()) 