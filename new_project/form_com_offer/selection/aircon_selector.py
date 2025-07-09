from sqlalchemy.orm import Session
from db import models
from utils.mylogger import Logger
from typing import List, Optional

logger = Logger("aircon_selector", "aircon_selector.log")

def calculate_required_power(params: dict) -> float:
    """Рассчитывает требуемую мощность кондиционера по методике RFClimat.ru."""
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
        
        logger.info(f"Расчет мощности: площадь={area}м², высота={ceiling_height}м, "
                    f"освещенность={illumination}, люди={num_people}, активность={activity}, "
                    f"компьютеры={num_computers}, ТВ={num_tvs}, прочая техника={other_power}Вт")

        # Валидация критических параметров
        if area <= 0 or ceiling_height <= 0:
            raise ValueError("Площадь и высота должны быть положительными значениями")
        
        # Коэффициенты освещенности и активности
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
        logger.error(f"Ошибка расчета мощности: {str(e)}")
        # Резервный расчёт по упрощённой методике
        return float(params.get("area", 0)) / 10

def select_aircons(db: Session, params: dict) -> List[models.AirConditioner]:
    """
    Подбирает кондиционеры из БД по заданным параметрам.

    Args:
        db: Сессия SQLAlchemy.
        params: Словарь с параметрами для фильтрации.
                - 'area': площадь помещения (кв.м.)
                - 'price_limit': максимальная цена (BYN)
                - 'brand': бренд
                - 'inverter': наличие инвертора (bool)
                - 'wifi': наличие Wi-Fi (bool)
                - Дополнительные для расчёта мощности:
                    'ceiling_height': высота потолков (м)
                    'illumination': освещенность (0-2)
                    'num_people': количество людей
                    'activity': активность (0-4)
                    'num_computers': компьютеры
                    'num_tvs': телевизоры
                    'other_power': мощность техники (Вт)
                - пример словаря:/
                  params = {
                    'area': 20,
                    'ceiling_height': 3.0,
                    'illumination': 2,
                    'num_people': 3,
                    'activity': 2,
                    'num_computers': 2,
                    'num_tvs': 1,
                    'other_power': 500,
                    ... другие параметры
                }

    Returns:
        Список подходящих объектов models.AirConditioner.
    """
    logger.info(f"Начат подбор кондиционеров с параметрами: {params}")
    
    try:
        # Расчёт требуемой мощности
        required_power_kw = calculate_required_power(params)
        logger.info(f"Требуемая мощность с запасом: {required_power_kw:.2f} кВт")
        
        query = db.query(models.AirConditioner)
        
        # Обязательный фильтр: наличие цены
        query = query.filter(models.AirConditioner.retail_price_byn.isnot(None))
        
        # Фильтр по мощности
        min_power = required_power_kw
        max_power = required_power_kw * 1.3  # +30% запас сверху
        query = query.filter(models.AirConditioner.cooling_power_kw >= min_power)
        query = query.filter(models.AirConditioner.cooling_power_kw <= max_power)
        
        # Фильтр по цене
        if "price_limit" in params and params["price_limit"]:
            try:
                price_limit = float(params["price_limit"])
                query = query.filter(models.AirConditioner.retail_price_byn <= price_limit)
                logger.info(f"Применен фильтр по цене: <= {price_limit} BYN")
            except (ValueError, TypeError):
                logger.warning("Некорректное значение price_limit. Фильтр не применен")
        
        # Фильтр по бренду
        if params.get("brand") and params["brand"] != "Любой":
            query = query.filter(models.AirConditioner.brand == params["brand"])
            logger.info(f"Применен фильтр по бренду: {params['brand']}")
        
        # Фильтр по инвертору (если есть в модели)
        if "inverter" in params and params["inverter"] is not None:
            # Предположим, что в модели есть поле 'has_inverter'
            # query = query.filter(models.AirConditioner.has_inverter == params["inverter"])
            logger.info(f"Фильтр по инвертору: {params['inverter']} (заглушка)")
        
        # Фильтр по Wi-Fi (если есть в модели)
        if "wifi" in params and params["wifi"] is not None:
            # Предположим, что в модели есть поле 'has_wifi'
            # query = query.filter(models.AirConditioner.has_wifi == params["wifi"])
            logger.info(f"Фильтр по Wi-Fi: {params['wifi']} (заглушка)")
        
        selected = query.all()
        logger.info(f"Подбор завершен. Найдено {len(selected)} моделей.")
        return selected
        
    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {str(e)}")
        return []