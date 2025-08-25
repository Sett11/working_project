"""
Модуль для обновления базы данных комплектующих из JSON-файла.

Этот модуль позволяет обновлять каталог комплектующих, не затрагивая
данные клиентов и заказов. Используется для синхронизации с актуальным
каталогом комплектующих.
"""
import json
import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from . import models, schemas
from .database import AsyncSessionLocal, engine, Base
from utils.mylogger import Logger

logger = Logger(name=__name__, log_file="db.log")

COMPONENTS_CATALOG_PATH = 'docs/components_catalog.json'


async def create_tables():
    """Проверка и создание таблиц в базе данных."""
    logger.info("Проверка и создание таблиц в базе данных...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Проверка и создание таблиц завершены.")


async def update_components_catalog():
    """
    Обновляет каталог комплектующих из JSON-файла.
    
    Полностью заменяет данные в таблице components, не затрагивая
    другие таблицы (clients, orders, air_conditioners).
    """
    await create_tables()
    
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Начинается обновление каталога комплектующих...")
            
            # Проверяем существование файла каталога
            if not os.path.exists(COMPONENTS_CATALOG_PATH):
                logger.error(f"Файл {COMPONENTS_CATALOG_PATH} не найден!")
                return False
            
            # Читаем данные из JSON-файла
            with open(COMPONENTS_CATALOG_PATH, 'r', encoding='utf-8') as f:
                components_data = json.load(f)
            
            # Получаем информацию о каталоге
            catalog_info = components_data.get("catalog_info", {})
            global_currency = catalog_info.get("currency", "BYN")
            total_components = catalog_info.get("total_components", 0)
            
            logger.info(f"Каталог: {catalog_info.get('name', 'Неизвестно')}")
            logger.info(f"Версия: {catalog_info.get('version', 'Неизвестно')}")
            logger.info(f"Всего комплектующих: {total_components}")
            logger.info(f"Валюта: {global_currency}")
            
            # Получаем список комплектующих
            components_to_add = components_data.get("components", [])
            
            if not components_to_add:
                logger.warning("Список комплектующих пуст!")
                return False
            
            # Подсчитываем существующие записи
            stmt_count = select(func.count()).select_from(models.Component)
            result = await db.execute(stmt_count)
            existing_count = result.scalar()
            
            logger.info(f"Найдено {existing_count} существующих записей комплектующих")
            
            # Очищаем таблицу комплектующих
            if existing_count > 0:
                logger.info("Очистка существующих записей комплектующих...")
                await db.execute(delete(models.Component))
                await db.commit()
                logger.info("Таблица комплектующих очищена.")
            
            # Добавляем новые записи
            added_count = 0
            skipped_count = 0
            
            for comp_data in components_to_add:
                try:
                    # Проверяем обязательные поля
                    comp_id = comp_data.get("id", "Unknown")
                    name = comp_data.get("name")
                    
                    if not name:
                        logger.warning(f"Пропуск записи с ID {comp_id}: отсутствует name")
                        skipped_count += 1
                        continue
                    
                    # Проверяем на дубликаты по имени
                    stmt = select(models.Component).where(models.Component.name == name)
                    result = await db.execute(stmt)
                    existing_comp = result.scalar()
                    
                    if existing_comp:
                        logger.warning(f"Пропуск записи с ID {comp_id}: дубликат name {name}")
                        skipped_count += 1
                        continue
                    
                    # Создаем Pydantic-схему для валидации
                    comp_schema = schemas.ComponentCreate(
                        name=name,
                        category=comp_data.get("category"),
                        price=comp_data.get("price"),
                        size=comp_data.get("size"),
                        material=comp_data.get("material"),
                        characteristics=comp_data.get("characteristics"),
                        currency=global_currency,
                        manufacturer=comp_data.get("manufacturer"),
                        in_stock=comp_data.get("in_stock", True),
                        description=comp_data.get("description"),
                        image_url=comp_data.get("image_path")
                    )
                    
                    # Создаем объект модели и добавляем в БД
                    db_comp = models.Component(**comp_schema.model_dump())
                    db.add(db_comp)
                    
                    # Коммитим каждую запись отдельно для лучшего контроля ошибок
                    await db.commit()
                    added_count += 1
                    
                    if added_count % 10 == 0:  # Логируем прогресс каждые 10 записей
                        logger.info(f"Добавлено {added_count} комплектующих...")
                        
                except Exception as e:
                    logger.error(f"Ошибка при добавлении комплектующего {comp_data.get('name', 'Unknown')}: {e}")
                    await db.rollback()
                    skipped_count += 1
                    continue
            
            logger.info(f"Обновление каталога комплектующих завершено!")
            logger.info(f"Добавлено: {added_count}")
            logger.info(f"Пропущено: {skipped_count}")
            logger.info(f"Всего обработано: {added_count + skipped_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Произошла ошибка во время обновления каталога комплектующих: {e}", exc_info=True)
            await db.rollback()
            return False
        finally:
            logger.debug("Закрытие сессии базы данных.")


async def main():
    """Основная функция для запуска обновления."""
    logger.info("Запуск обновления каталога комплектующих...")
    success = await update_components_catalog()
    
    if success:
        logger.info("Обновление каталога комплектующих выполнено успешно!")
    else:
        logger.error("Обновление каталога комплектующих завершилось с ошибками!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main()) 