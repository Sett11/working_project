"""
Модуль подбора кондиционеров и расчёта требуемой мощности.

Содержит:
- Функцию расчёта требуемой мощности кондиционера по методике RFClimat.ru
- Функцию подбора кондиционеров из БД по заданным параметрам
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import models
from utils.mylogger import Logger
from typing import List, Optional

# Инициализация логгера для подбора кондиционеров.
# log_file указывается без папки logs, чтобы использовать дефолтную директорию логов.
logger = Logger("aircon_selector", "aircon_selector.log")

def calculate_required_power(params: dict) -> float:
    """
    Рассчитывает требуемую мощность кондиционера по методике RFClimat.ru.

    Args:
        params (dict): Словарь с параметрами помещения и нагрузки.
            - area: площадь помещения (м²)
            - ceiling_height: высота потолков (м)
            - illumination: уровень освещённости (0-2)
            - num_people: количество людей
            - activity: уровень активности (0-4)
            - num_computers: количество компьютеров
            - num_tvs: количество телевизоров
            - other_power: мощность прочей техники (Вт)

    Returns:
        float: Требуемая мощность охлаждения (кВт)
    """
    try:
        # Извлекаем параметры с значениями по умолчанию
        area = float(params.get("area", 0))
        ceiling_height = float(params.get("ceiling_height", 2.7))
        illumination = int(params.get("illumination", 1))
        num_people = int(params.get("num_people", 1))
        activity = int(params.get("activity", 1))
        num_computers = int(params.get("num_computers", 0))
        num_tvs = int(params.get("num_tvs", 0))
        other_power = float(params.get("other_power", 0))
        
        logger.info(f"Расчёт мощности: площадь={area}м², высота={ceiling_height}м, "
                    f"освещённость={illumination}, люди={num_people}, активность={activity}, "
                    f"компьютеры={num_computers}, ТВ={num_tvs}, прочая техника={other_power}Вт")

        # Валидация критических параметров
        if area <= 0 or ceiling_height <= 0:
            raise ValueError("Площадь и высота должны быть положительными значениями")
        
        # Коэффициенты освещённости и активности
        illumination_coeffs = [30, 35, 40]
        activity_coeffs = [100, 125, 150, 200, 300]
        
        # Проверка корректности индексов
        if illumination < 0 or illumination >= len(illumination_coeffs):
            illumination = 1
        if activity < 0 or activity >= len(activity_coeffs):
            activity = 1
            
        q = illumination_coeffs[illumination]
        people_power = activity_coeffs[activity]
        
        # Расчёт теплопритоков (Вт)
        Q1 = area * ceiling_height * q  # От ограждающих конструкций
        Q2 = num_people * people_power  # От людей
        Q3 = (num_computers * 300 + num_tvs * 200 + other_power) * 0.3  # От техники
        
        # Суммарные теплопритоки (кВт)
        total_Q = (Q1 + Q2 + Q3) / 1000
        
        # Добавление запаса мощности 20%
        required_power = total_Q * 1.2
        
        logger.info(f"Рассчитанная мощность: {required_power:.2f} кВт (Q1={Q1}Вт, Q2={Q2}Вт, Q3={Q3}Вт)")
        return required_power
        
    except Exception as e:
        logger.error(f"Ошибка расчёта мощности: {str(e)}")
        # Резервный расчёт по упрощённой методике
        return float(params.get("area", 0)) / 10

async def select_aircons(db: AsyncSession, params: dict) -> list[models.AirConditioner]:
    """
    Подбирает кондиционеры из БД по заданным параметрам.

    Args:
        db: Сессия SQLAlchemy.
        params: Словарь с параметрами для фильтрации.
            - area: площадь помещения (кв.м.)
            - price_limit: максимальная цена (BYN)
            - brand: бренд
            - inverter: наличие инвертора (bool)
            - wifi: наличие Wi-Fi (bool)
                - Дополнительные для расчёта мощности:
                ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power

    Returns:
        Список подходящих объектов models.AirConditioner.
    """
    logger.info(f"Начат подбор кондиционеров с параметрами: {params}")
    
    try:
        # Расчёт требуемой мощности
        required_power_kw = calculate_required_power(params)
        logger.info(f"Требуемая мощность с запасом: {required_power_kw:.2f} кВт")

        # Формируем асинхронный запрос к БД
        stmt = select(models.AirConditioner)

        # Обязательный фильтр: наличие цены
        stmt = stmt.where(models.AirConditioner.retail_price_byn.isnot(None))

        # Фильтр по мощности
        min_power = required_power_kw
        max_power = required_power_kw * 1.3  # +30% запас сверху
        stmt = stmt.where(models.AirConditioner.cooling_power_kw >= min_power)
        stmt = stmt.where(models.AirConditioner.cooling_power_kw <= max_power)

        # Фильтр по цене
        if "price_limit" in params and params["price_limit"]:
            try:
                price_limit = float(params["price_limit"])
                stmt = stmt.where(models.AirConditioner.retail_price_byn <= price_limit)
                logger.info(f"Применён фильтр по цене: <= {price_limit} BYN")
            except (ValueError, TypeError):
                logger.warning("Некорректное значение price_limit. Фильтр не применён")

        # Фильтр по бренду
        if params.get("brand") and params["brand"] != "Любой":
            stmt = stmt.where(models.AirConditioner.brand == params["brand"])
            logger.info(f"Применён фильтр по бренду: {params['brand']}")

        # Фильтр по инвертору
        if "inverter" in params and params["inverter"] is not None:
            stmt = stmt.where(models.AirConditioner.is_inverter == params["inverter"])
            logger.info(f"Применён фильтр по инвертору: {params['inverter']}")

        # Фильтр по Wi-Fi
        if "wifi" in params and params["wifi"] is not None:
            stmt = stmt.where(models.AirConditioner.has_wifi == params["wifi"])
            logger.info(f"Применён фильтр по Wi-Fi: {params['wifi']}")

        # Фильтр по типу монтажа
        if "mount_type" in params and params["mount_type"] and params["mount_type"] != "Любой":
            stmt = stmt.where(models.AirConditioner.mount_type == params["mount_type"])
            logger.info(f"Применён фильтр по типу монтажа: {params['mount_type']}")

        result = await db.execute(stmt)
        selected = result.scalars().all()
        logger.info(f"Подбор завершён. Найдено {len(selected)} моделей.")
        return selected

    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {str(e)}")
        return []