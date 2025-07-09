from sqlalchemy.orm import Session
from db import models
from utils.mylogger import Logger

logger = Logger("materials_calculator", "materials_calculator.log")

def calculate_materials(db: Session, order: models.Order, selected_aircons: list[models.AirConditioner]) -> list[models.Component]:
    """
    Подбирает необходимые комплектующие для заказа.
    
    Args:
        db: Сессия SQLAlchemy.
        order: Объект заказа.
        selected_aircons: Список выбранных кондиционеров.

    Returns:
        Список объектов models.Component с рассчитанным количеством.
    """
    logger.info(f"Начат расчет комплектующих для заказа ID: {order.id}")
    
    required_components = []
    
    # --- Логика подбора ---
    # На данном этапе реализуем простую логику:
    # для каждого кондиционера в заказе добавляем стандартный монтажный комплект.
    
    if not selected_aircons:
        logger.warning("В заказе нет кондиционеров, комплектующие не рассчитывались.")
        return []

    # Условно, стандартный комплект - это трубы, кронштейн и кабель.
    # Ищем их в базе по имени.
    
    # TODO: Сделать эту логику более гибкой, возможно, на основе характеристик кондиционера.
    
    for aircon in selected_aircons:
        # 1. Медная труба (2 шт разного диаметра)
        # Диаметр труб берем из спецификации кондиционера
        if aircon.pipe_diameter:
            diameters = aircon.pipe_diameter.replace('"', '').replace("'", "").split('/')
            if len(diameters) == 2:
                # Условно, для монтажа нужно по 5 метров каждой трубы
                # Здесь можно будет добавить логику расчета длины трассы
                pass # Пока не добавляем, чтобы не усложнять

        # 2. Кронштейн (1 шт)
        bracket = db.query(models.Component).filter(models.Component.name.like("%Кронштейн%")).first()
        if bracket:
            # Здесь можно было бы добавить расчет количества, но для кронштейна это 1
            required_components.append(bracket)

        # 3. Кабель (условно 5 метров)
        cable = db.query(models.Component).filter(models.Component.name.like("%Кабель%")).first()
        if cable:
            # Здесь можно добавить расчет длины
            required_components.append(cable)

    component_names = [c.name for c in required_components]
    logger.info(f"Расчет завершен. Подобраны комплектующие: {component_names}")
    
    return required_components
