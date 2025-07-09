from sqlalchemy.orm import Session
from db import models
from utils.mylogger import Logger

logger = Logger("aircon_selector", "logs/aircon_selector.log")

def select_aircons(db: Session, params: dict) -> list[models.AirConditioner]:
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

    Returns:
        Список подходящих объектов models.AirConditioner.
    """
    logger.info(f"Начат подбор кондиционеров с параметрами: {params}")
    
    query = db.query(models.AirConditioner)
    
    # 0. ОБЯЗАТЕЛЬНЫЙ ФИЛЬТР: у кондиционера должна быть цена
    query = query.filter(models.AirConditioner.retail_price_byn.isnot(None))
    
    # 1. Фильтр по мощности (основной критерий)
    # Простое правило: 1 кВт мощности на 10 кв.м.
    required_power_kw = params.get("area", 0) / 10
    # Ищем кондиционеры с мощностью >= требуемой, но не слишком большой (+30%)
    query = query.filter(models.AirConditioner.cooling_power_kw >= required_power_kw)
    query = query.filter(models.AirConditioner.cooling_power_kw <= required_power_kw * 1.3)
    
    # 2. Фильтр по цене
    if params.get("price_limit"):
        try:
            price_limit = float(params["price_limit"])
            query = query.filter(models.AirConditioner.retail_price_byn <= price_limit)
        except (ValueError, TypeError):
            logger.warning(f"Некорректный лимит цены: {params['price_limit']}. Фильтр по цене не применяется.")

    # 3. Фильтр по бренду
    if params.get("brand") and params["brand"] != "Любой":
        query = query.filter(models.AirConditioner.brand == params["brand"])
        
    # TODO: Добавить фильтры по 'inverter' и 'wifi', когда эти поля будут в модели
    # if params.get("inverter") is not None:
    #     query = query.filter(models.AirConditioner.has_inverter == params["inverter"])
    # if params.get("wifi") is not None:
    #     query = query.filter(models.AirConditioner.has_wifi == params["wifi"])

    selected = query.all()
    
    logger.info(f"Подбор завершен. Найдено {len(selected)} моделей.")
    
    return selected
