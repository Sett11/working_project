"""
Модуль для обновления базы данных кондиционеров из JSON-файла.

Этот модуль позволяет обновлять каталог кондиционеров, не затрагивая
данные клиентов и заказов. Используется для синхронизации с актуальным
каталогом кондиционеров.
"""
import json
import re
import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from . import models, schemas
from .database import AsyncSessionLocal, engine, Base
from utils.mylogger import Logger

logger = Logger(name=__name__, log_file="db.log")

AIRS_CATALOG_PATH = 'docs/airs.json'


async def create_tables():
    """Проверка и создание таблиц в базе данных."""
    logger.info("Проверка и создание таблиц в базе данных...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Проверка и создание таблиц завершены.")


async def update_air_conditioners_catalog():
    """
    Обновляет каталог кондиционеров из JSON-файла.
    
    Полностью заменяет данные в таблице air_conditioners, не затрагивая
    другие таблицы (clients, orders, components).
    """
    await create_tables()
    
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Начинается обновление каталога кондиционеров...")
            
            # Проверяем существование файла каталога
            if not os.path.exists(AIRS_CATALOG_PATH):
                logger.error(f"Файл {AIRS_CATALOG_PATH} не найден!")
                return False
            
            # Читаем данные из JSON-файла
            with open(AIRS_CATALOG_PATH, 'r', encoding='utf-8') as f:
                airs_data = json.load(f)
            
            # Получаем список кондиционеров
            air_conditioners_to_add = airs_data.get("air_conditioners", [])
            
            if not air_conditioners_to_add:
                logger.warning("Список кондиционеров пуст!")
                return False
            
            logger.info(f"Найдено {len(air_conditioners_to_add)} кондиционеров в каталоге")
            
            # Подсчитываем существующие записи
            stmt_count = select(func.count()).select_from(models.AirConditioner)
            result = await db.execute(stmt_count)
            existing_count = result.scalar()
            
            logger.info(f"Найдено {existing_count} существующих записей кондиционеров")
            
            # Очищаем таблицу кондиционеров
            if existing_count > 0:
                logger.info("Очистка существующих записей кондиционеров...")
                await db.execute(delete(models.AirConditioner))
                await db.commit()
                logger.info("Таблица кондиционеров очищена.")
            
            # Добавляем новые записи
            added_count = 0
            skipped_count = 0
            
            for air_con_data in air_conditioners_to_add:
                try:
                    # Проверяем обязательные поля
                    record_id = air_con_data.get("id", "Unknown")
                    model_name = air_con_data.get("model_name")
                    
                    if not model_name:
                        logger.warning(f"Пропуск записи с ID {record_id}: отсутствует model_name")
                        skipped_count += 1
                        continue
                    
                    # Проверяем на дубликаты по model_name
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
                    
                    # Обрабатываем цену
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
                    
                    # Создаем Pydantic-схему для валидации
                    air_con_schema = schemas.AirConditionerCreate(
                        model_name=model_name,
                        brand=air_con_data.get("brand"),
                        series=air_con_data.get("series"),
                        # Прямые пути к полям в новой структуре
                        cooling_power_kw=air_con_data.get("cooling_power_kw"),
                        heating_power_kw=None,  # В новой структуре нет heating_power_kw
                        pipe_diameter=None,  # В новой структуре нет pipe_diameter
                        energy_efficiency_class=energy_class,
                        retail_price_byn=retail_price_byn,
                        description=description,
                        air_description=None,  # Старое поле больше не нужно
                        representative_image=None,  # В новой структуре нет representative_image
                        is_inverter=is_inverter,
                        has_wifi=has_wifi,
                        mount_type=mount_type
                    )
                    
                    # Создаем объект модели и добавляем в БД
                    db_air_con = models.AirConditioner(**air_con_schema.model_dump())
                    db.add(db_air_con)
                    
                    # Коммитим каждую запись отдельно для лучшего контроля ошибок
                    await db.commit()
                    added_count += 1
                    
                    if added_count % 50 == 0:  # Логируем прогресс каждые 50 записей
                        logger.info(f"Добавлено {added_count} кондиционеров...")
                        
                except Exception as e:
                    logger.error(f"Ошибка при добавлении кондиционера {air_con_data.get('model_name', 'Unknown')}: {e}")
                    await db.rollback()
                    skipped_count += 1
                    continue
            
            logger.info(f"Обновление каталога кондиционеров завершено!")
            logger.info(f"Добавлено: {added_count}")
            logger.info(f"Пропущено: {skipped_count}")
            logger.info(f"Всего обработано: {added_count + skipped_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Произошла ошибка во время обновления каталога кондиционеров: {e}", exc_info=True)
            await db.rollback()
            return False
        finally:
            logger.debug("Закрытие сессии базы данных.")


async def main():
    """Основная функция для запуска обновления."""
    logger.info("Запуск обновления каталога кондиционеров...")
    success = await update_air_conditioners_catalog()
    
    if success:
        logger.info("Обновление каталога кондиционеров выполнено успешно!")
    else:
        logger.error("Обновление каталога кондиционеров завершилось с ошибками!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main()) 