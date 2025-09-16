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
        # Словари для преобразования строковых значений в индексы
        illumination_map = {"слабая": 0, "средняя": 1, "сильная": 2, "Слабая": 0, "Средняя": 1, "Сильная": 2}
        activity_map = {"сидячая работа": 0, "легкая работа": 1, "средняя работа": 2, "тяжелая работа": 3, "спорт": 4, 
                       "Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
        # Извлекаем параметры с значениями по умолчанию
        area = float(params.get("area", 0))
        ceiling_height = float(params.get("ceiling_height", 2.7))
        # --- Корректное преобразование освещённости ---
        illumination_raw = params.get("illumination", 1)
        if isinstance(illumination_raw, str):
            illumination = illumination_map.get(illumination_raw.strip().lower(), 1)
        else:
            illumination = int(illumination_raw)
        # --- Корректное преобразование активности ---
        activity_raw = params.get("activity", 1)
        if isinstance(activity_raw, str):
            activity = activity_map.get(activity_raw.strip().lower(), 1)
        else:
            activity = int(activity_raw)
        num_people = int(params.get("num_people", 1))
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
    Подбирает кондиционеры из БД по заданным параметрам с fallback логикой.

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

        # Fallback логика: если не найдено кондиционеров, увеличиваем max_power
        max_power_limit = 23.0
        power_increment = 0.1  # 10% за итерацию
        max_attempts = 10
        
        for attempt in range(max_attempts):
            # Рассчитываем max_power для текущей попытки
            max_power_multiplier = 1.1 + (attempt * power_increment)  # 1.1, 1.2, 1.3, ...
            current_max_power = required_power_kw * max_power_multiplier
            
            logger.info(f"Попытка {attempt + 1}: max_power = {current_max_power:.2f} кВт (множитель: {max_power_multiplier:.1f})")
            
            # Проверяем лимит максимальной мощности
            if current_max_power > max_power_limit:
                logger.warning(f"Достигнут лимит максимальной мощности {max_power_limit} кВт. Поиск прекращён.")
                break
            
            # Выполняем подбор с текущими параметрами
            selected = await _select_aircons_core(db, params, required_power_kw, current_max_power)
            
            if selected:
                logger.info(f"Найдено {len(selected)} кондиционеров на попытке {attempt + 1}")
                return selected
            else:
                logger.info(f"На попытке {attempt + 1} кондиционеры не найдены. Увеличиваем max_power.")
        
        logger.warning("Не удалось найти кондиционеры даже с увеличенной мощностью")
        return []

    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {str(e)}")
        return []

async def _select_aircons_core(db: AsyncSession, params: dict, min_power: float, max_power: float) -> list[models.AirConditioner]:
    """
    Внутренняя функция для выполнения подбора кондиционеров с заданными параметрами мощности.
    
    Args:
        db: Сессия SQLAlchemy
        params: Параметры фильтрации
        min_power: Минимальная мощность (кВт)
        max_power: Максимальная мощность (кВт)
        
    Returns:
        Список подобранных кондиционеров
    """
    try:
        # Формируем асинхронный запрос к БД
        stmt = select(models.AirConditioner)

        # Обязательный фильтр: наличие цены
        stmt = stmt.where(models.AirConditioner.retail_price_byn.isnot(None))

        # Фильтр по мощности
        stmt = stmt.where(models.AirConditioner.cooling_power_kw >= min_power)
        stmt = stmt.where(models.AirConditioner.cooling_power_kw <= max_power)

        # Фильтр по цене
        if "price_limit" in params and params["price_limit"] is not None:
            try:
                price_limit = float(params["price_limit"])
                stmt = stmt.where(models.AirConditioner.retail_price_byn <= price_limit)
                logger.info(f"Применён фильтр по цене: <= {price_limit} BYN")
            except (ValueError, TypeError):
                logger.warning("Некорректное значение price_limit. Фильтр не применён")
        else:
            logger.warning(f"Некорректное значение price_limit = {params['price_limit']}. Фильтр не применён")

        # Фильтр по бренду
        if params.get("brand") and params["brand"] != "Любой":
            stmt = stmt.where(models.AirConditioner.brand == params["brand"])
            logger.info(f"Применён фильтр по бренду: {params['brand']}")
        else:
            logger.warning(f"Некорректное значение brand = {params['brand']}. Фильтр не применён")

        # Фильтр по инвертору
        if "inverter" in params and params["inverter"] is not None:
            stmt = stmt.where(models.AirConditioner.is_inverter == params["inverter"])
            logger.info(f"Применён фильтр по инвертору: {params['inverter']}")
        else:
            logger.warning(f"Некорректное значение inverter = {params['inverter']}. Фильтр не применён")

        # Фильтр по Wi-Fi
        if "wifi" in params and params["wifi"] is not None:
            stmt = stmt.where(models.AirConditioner.has_wifi == params["wifi"])
            logger.info(f"Применён фильтр по Wi-Fi: {params['wifi']}")
        else:
            logger.warning(f"Некорректное значение wifi = {params['wifi']}. Фильтр не применён")

        # Фильтр по типу монтажа
        if "mount_type" in params and params["mount_type"] and params["mount_type"] != "Любой":
            stmt = stmt.where(models.AirConditioner.mount_type == params["mount_type"])
            logger.info(f"Применён фильтр по типу монтажа: {params['mount_type']}")
        else:
            logger.warning(f"Некорректное значение mount_type = {params['mount_type']}. Фильтр не применён")
        
        result = await db.execute(stmt)
        selected = result.scalars().all()
        return selected

    except Exception as e:
        logger.error(f"Ошибка при выполнении подбора кондиционеров: {str(e)}")
        return []