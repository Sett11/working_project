"""
Модуль подбора кондиционеров для составных заказов.

Содержит функции для подбора кондиционеров в заказах с несколькими кондиционерами
для одного клиента.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import models
from utils.mylogger import Logger
from utils.aircon_selector import calculate_required_power

# Инициализация логгера для подбора кондиционеров в составных заказах
logger = Logger("compose_aircon_selector", "compose_aircon_selector.log")

async def select_aircons_for_compose_order(db: AsyncSession, compose_order_data: dict) -> dict:
    """
    Подбирает кондиционеры для составного заказа с несколькими кондиционерами.
    
    Args:
        db (AsyncSession): Сессия базы данных
        compose_order_data (dict): Данные составного заказа
        
    Returns:
        dict: Результат подбора для каждого кондиционера в заказе
    """
    try:
        client_data = compose_order_data.get("client_data", {})
        airs = compose_order_data.get("airs", [])
        
        logger.info(f"Подбор кондиционеров для составного заказа клиента: {client_data.get('full_name', 'N/A')}")
        logger.info(f"Количество кондиционеров в заказе: {len(airs)}")
        
        results = {
            "client_data": client_data,
            "aircon_results": [],
            "total_count": len(airs)
        }
        
        for i, air in enumerate(airs):
            logger.info(f"Подбор кондиционера #{i+1} (ID: {air.get('id')})")
            
            # Извлекаем параметры для текущего кондиционера
            aircon_params = air.get("aircon_params", {})
            order_params = air.get("order_params", {})
            
            # Формируем параметры для подбора (передаем все параметры для правильного расчета мощности)
            selection_params = {
                "area": aircon_params.get("area", 0),
                "ceiling_height": aircon_params.get("ceiling_height", 2.7),
                "illumination": aircon_params.get("illumination", "Средняя"),
                "num_people": aircon_params.get("num_people", 1),
                "activity": aircon_params.get("activity", "Сидячая работа"),
                "num_computers": aircon_params.get("num_computers", 0),
                "num_tvs": aircon_params.get("num_tvs", 0),
                "other_power": aircon_params.get("other_power", 0),
                "brand": aircon_params.get("brand", "Любой"),
                "price_limit": aircon_params.get("price_limit", 22000),
                "inverter": aircon_params.get("inverter", False),
                "wifi": aircon_params.get("wifi", False),
                "mount_type": aircon_params.get("mount_type", "Любой")
            }
            
            # Подбираем кондиционеры для текущих параметров
            selected_aircons = await select_aircons_for_params(db, selection_params)
            
            # Рассчитываем требуемую мощность для отображения в результате
            required_power = calculate_required_power(aircon_params)
            
            # Формируем результат для текущего кондиционера
            aircon_result = {
                "order_index": i + 1,
                "air_id": air.get("id"),
                "aircon_params": aircon_params,
                "order_params": order_params,
                "required_power": required_power,
                "selected_aircons": selected_aircons,
                "selected_count": len(selected_aircons)
            }
            
            results["aircon_results"].append(aircon_result)
            
            logger.info(f"Для кондиционера #{i+1} (ID: {air.get('id')}) подобрано {len(selected_aircons)} вариантов")
        
        logger.info(f"Подбор кондиционеров для составного заказа завершен. Всего подобрано: {sum(r['selected_count'] for r in results['aircon_results'])}")
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров для составного заказа: {e}", exc_info=True)
        raise

async def select_aircons_for_params(db: AsyncSession, params: dict) -> list[models.AirConditioner]:
    """
    Подбирает кондиционеры по заданным параметрам (использует тот же алгоритм, что и aircon_selector.py).
    
    Args:
        db (AsyncSession): Сессия базы данных
        params (dict): Параметры для подбора
        
    Returns:
        list[models.AirConditioner]: Список подобранных кондиционеров
    """
    try:
        # Расчёт требуемой мощности
        required_power_kw = calculate_required_power(params)
        logger.info(f"Требуемая мощность с запасом: {required_power_kw:.2f} кВт")

        # Формируем асинхронный запрос к БД
        stmt = select(models.AirConditioner)

        # Обязательный фильтр: наличие цены
        stmt = stmt.where(models.AirConditioner.retail_price_byn.isnot(None))

        # Фильтр по мощности (используем тот же алгоритм, что и в основном aircon_selector)
        min_power = required_power_kw
        max_power = required_power_kw * 1.3  # +30% запас сверху
        stmt = stmt.where(models.AirConditioner.cooling_power_kw >= min_power)
        stmt = stmt.where(models.AirConditioner.cooling_power_kw <= max_power)

        # Фильтр по цене
        price_limit = params.get("price_limit")
        if price_limit is not None:
            try:
                price_limit = float(price_limit)
                stmt = stmt.where(models.AirConditioner.retail_price_byn <= price_limit)
                logger.info(f"Применён фильтр по цене: <= {price_limit} BYN")
            except (ValueError, TypeError):
                logger.warning("Некорректное значение price_limit. Фильтр не применён")

        # Фильтр по бренду
        brand = params.get("brand")
        if brand and brand != "Любой":
            stmt = stmt.where(models.AirConditioner.brand == brand)
            logger.info(f"Применён фильтр по бренду: {brand}")

        # Фильтр по инвертору
        inverter = params.get("inverter")
        if inverter is not None:
            stmt = stmt.where(models.AirConditioner.is_inverter == inverter)
            logger.info(f"Применён фильтр по инвертору: {inverter}")

        # Фильтр по Wi-Fi
        wifi = params.get("wifi")
        if wifi is not None:
            stmt = stmt.where(models.AirConditioner.has_wifi == wifi)
            logger.info(f"Применён фильтр по Wi-Fi: {wifi}")

        # Фильтр по типу монтажа
        mount_type = params.get("mount_type")
        if mount_type and mount_type != "Любой":
            stmt = stmt.where(models.AirConditioner.mount_type == mount_type)
            logger.info(f"Применён фильтр по типу монтажа: {mount_type}")
        
        result = await db.execute(stmt)
        selected = result.scalars().all()
        logger.info(f"Подбор завершён. Найдено {len(selected)} моделей.")
        return selected

    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {str(e)}")
        return []
