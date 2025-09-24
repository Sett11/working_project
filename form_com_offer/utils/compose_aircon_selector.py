"""
Модуль подбора кондиционеров для составных заказов.

Содержит функции для подбора кондиционеров в заказах с несколькими кондиционерами
для одного клиента.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import models
from utils.mylogger import Logger

# Инициализация логгера для подбора кондиционеров в составных заказах
logger = Logger("compose_aircon_selector", "compose_aircon_selector.log")

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
    Подбирает кондиционеры по заданным параметрам с fallback логикой (использует тот же алгоритм, что и aircon_selector.py).
    
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
            selected = await _select_aircons_for_params_core(db, params, required_power_kw, current_max_power)
            
            if selected:
                logger.info(f"Найдено {len(selected)} кондиционеров на попытке {attempt + 1}")
                return selected
            else:
                logger.info(f"На попытке {attempt + 1} кондиционеры не найдены. Увеличиваем max_power.")
        
        logger.warning("Не удалось найти кондиционеры даже с увеличенной мощностью")
        return []

    except Exception as e:
        logger.error(f"Ошибка при подборе кондиционеров: {str(e)}", exc_info=True)
        return []

async def _select_aircons_for_params_core(db: AsyncSession, params: dict, min_power: float, max_power: float) -> list[models.AirConditioner]:
    """
    Внутренняя функция для выполнения подбора кондиционеров с заданными параметрами мощности.
    
    Args:
        db (AsyncSession): Сессия базы данных
        params (dict): Параметры фильтрации
        min_power (float): Минимальная мощность (кВт)
        max_power (float): Максимальная мощность (кВт)
        
    Returns:
        list[models.AirConditioner]: Список подобранных кондиционеров
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
        return selected

    except Exception as e:
        logger.error(f"Ошибка при выполнении подбора кондиционеров: {str(e)}", exc_info=True)
        return []
