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

AIRS_CATALOG_PATH = 'docs/airs.json'
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
                    if not model_name or model_name.strip() == "moke":
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
                    
                    # --- НОВАЯ ЛОГИКА ИЗВЛЕЧЕНИЯ ДАННЫХ ИЗ ПЛОСКОЙ СТРУКТУРЫ ---
                    
                    # Определяем наличие инвертора и Wi-Fi по полям is_inverter и has_wifi
                    # Обрабатываем случаи, когда поля содержат пустые строки или невалидные значения
                    is_inverter_raw = air_con_data.get("is_inverter", False)
                    has_wifi_raw = air_con_data.get("has_wifi", False)
                    
                    # Преобразуем в булево значение
                    if isinstance(is_inverter_raw, bool):
                        is_inverter = is_inverter_raw
                    elif isinstance(is_inverter_raw, str) and is_inverter_raw.strip():
                        is_inverter = is_inverter_raw.lower() in ['true', '1', 'yes', 'да']
                    else:
                        is_inverter = False
                        
                    if isinstance(has_wifi_raw, bool):
                        has_wifi = has_wifi_raw
                    elif isinstance(has_wifi_raw, str) and has_wifi_raw.strip():
                        has_wifi = has_wifi_raw.lower() in ['true', '1', 'yes', 'да']
                    else:
                        has_wifi = False

                    # Определяем тип монтажа по полю mount_type
                    mount_type_raw = air_con_data.get("mount_type")
                    mount_type = mount_type_raw if mount_type_raw and mount_type_raw.strip() else None
                    
                    # Класс энергоэффективности из поля class
                    energy_class_raw = air_con_data.get("class", "N/A")
                    energy_class = energy_class_raw if energy_class_raw and energy_class_raw.strip() else "N/A"
                    
                    # Описание из поля description
                    description = air_con_data.get("description", "")

                    # --- ОБРАБОТКА ЦЕНЫ ---
                    retail_price_raw = air_con_data.get("retail_price_byn")
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
                        # Прямые пути к полям в новой структуре
                        cooling_power_kw=air_con_data.get("cooling_power_kw"),
                        heating_power_kw=None,  # В новой структуре нет heating_power_kw
                        pipe_diameter=None,  # В новой структуре нет pipe_diameter
                        energy_efficiency_class=energy_class,
                        # Цена
                        retail_price_byn=retail_price_byn,
                        # Описание
                        description=description,
                        air_description=None,  # Старое поле больше не нужно
                        representative_image=None,  # В новой структуре нет representative_image
                        # Новые флаги
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

            # --- 3. Инициализация счетчика КП ---
            logger.info("Инициализация счетчика коммерческих предложений...")
            try:
                # Проверяем, существует ли уже счетчик
                stmt_counter = select(models.OfferCounter).filter_by(id=0)
                result = await db.execute(stmt_counter)
                existing_counter = result.scalar_one_or_none()
                
                if not existing_counter:
                    # Создаем новый счетчик с начальным номером 0
                    counter = models.OfferCounter(id=0, current_number=0)
                    db.add(counter)
                    await db.commit()
                    logger.info("Счетчик КП инициализирован с номером 0.")
                else:
                    logger.info(f"Счетчик КП уже существует с номером {existing_counter.current_number}.")
                    
            except Exception as counter_error:
                logger.error(f"Ошибка при инициализации счетчика КП: {counter_error}")
                await db.rollback()

        except Exception as e:
            logger.error(f"Произошла ошибка во время наполнения БД: {e}", exc_info=True)
            await db.rollback()
        finally:
            logger.debug("Закрытие сессии базы данных.")

if __name__ == "__main__":
    asyncio.run(seed_data()) 