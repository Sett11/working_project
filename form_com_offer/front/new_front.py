"""
Новый модуль фронтенда Gradio для системы формирования коммерческих предложений по кондиционерам.

Основные изменения:
- Единственная вкладка "Формирование заказа" 
- Всплывающая вкладка "Комплектующие"
- Чекбоксы для выбора кондиционеров
- Модель room для сохранения данных комнаты
"""
import gradio as gr
import httpx
from utils.mylogger import Logger
import json
import os
from collections import defaultdict
import re
import datetime

# Импортируем необходимые функции из существующего front.py
from front.front import (
    COMPONENTS_CATALOG, get_placeholder_order,
    safe_float, safe_int, safe_bool,
    get_component_image_path,
    fetch_all_orders_list
)
from front.auth_interface import create_auth_interface, get_auth_manager, get_auth_status

# Инициализация логгера
logger = Logger(name=__name__, log_file="frontend.log")

# URL для backend API
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8001")

# Глобальные переменные для компонентов UI
components_ui_inputs = []
components_catalog_for_ui = []

# Глобальные переменные для хранения выбранного заказа
selected_order_id = None
loaded_order_data = {}
current_room_config = "Базовая конфигурация"  # Текущая выбранная конфигурация помещения

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАКАЗАМИ ===

def load_room_configurations_from_order(order_data):
    """Загружает список конфигураций из массива rooms + базовая конфигурация"""
    try:
        rooms = order_data.get("rooms", [])
        configs = ["Базовая конфигурация"]
        
        # Собираем все уникальные room_type из всех помещений
        unique_room_types = set()
        for i, room in enumerate(rooms):
            room_type = room.get("room_type", "").strip()
            if room_type:
                # Пропускаем rooms[0] если это базовая конфигурация без данных
                if i == 0 and (not room_type or room_type == "квартира"):
                    # Проверяем, является ли это реально базовой конфигурацией или пользовательским помещением
                    # Если у помещения есть кондиционеры или комплектующие, то это реальное помещение
                    has_aircons = bool(room.get("selected_aircons_for_room"))
                    has_components = bool(room.get("components_for_room"))
                    if has_aircons or has_components:
                        unique_room_types.add(room_type)
                else:
                    unique_room_types.add(room_type)
        
        # Добавляем все уникальные типы помещений в список конфигураций
        configs.extend(sorted(unique_room_types))
        
        logger.info(f"Загружено конфигураций помещений: {len(configs)} ({configs})")
        return configs
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигураций помещений: {e}")
        return ["Базовая конфигурация"]

def get_placeholder_room_data():
    """Возвращает базовые данные для помещения (из плейсхолдера)"""
    placeholder = get_placeholder_order()
    return {
        "area": placeholder["aircon_params"]["area"],
        "room_type": "",  # Пустое название, чтобы пользователь сам ввел уникальное
        "installation_price": placeholder["order_params"]["installation_price"],
        "brand": placeholder["aircon_params"]["brand"],
        "wifi": placeholder["aircon_params"]["wifi"],
        "inverter": placeholder["aircon_params"]["inverter"],
        "price_limit": placeholder["aircon_params"]["price_limit"],
        "mount_type": placeholder["aircon_params"]["mount_type"],
        "ceiling_height": placeholder["aircon_params"]["ceiling_height"],
        "illumination": placeholder["aircon_params"]["illumination"],
        "num_people": placeholder["aircon_params"]["num_people"],
        "activity": "Сидячая работа",
        "num_computers": placeholder["aircon_params"]["num_computers"],
        "num_tvs": placeholder["aircon_params"]["num_tvs"],
        "other_power": placeholder["aircon_params"]["other_power"],
        "comments": "Оставьте комментарий..."
    }

async def load_room_config_data(config_name, order_id_hidden_value):
    """Загружает данные конкретной конфигурации помещения"""
    global current_room_config
    try:
        # Обновляем текущую выбранную конфигурацию
        current_room_config = config_name
        
        if config_name == "Базовая конфигурация":
            # Возвращаем дефолтные значения из плейсхолдера
            base_data = get_placeholder_room_data()
            logger.info("Загружена базовая конфигурация помещения")
            return [
                gr.update(value=base_data["area"]),                    # room_area
                gr.update(value=base_data["room_type"]),               # room_type
                gr.update(value=base_data["installation_price"]),     # installation_price
                gr.update(value=base_data["brand"]),                   # brand
                gr.update(value=base_data["wifi"]),                    # wifi_support
                gr.update(value=base_data["inverter"]),                # inverter_type
                gr.update(value=base_data["price_limit"]),             # max_price
                gr.update(value=base_data["mount_type"]),              # mount_type
                gr.update(value=base_data["ceiling_height"]),          # ceiling_height
                gr.update(value=base_data["illumination"]),            # illumination
                gr.update(value=base_data["num_people"]),              # num_people
                gr.update(value=base_data["activity"]),                # activity
                gr.update(value=base_data["num_computers"]),           # num_computers
                gr.update(value=base_data["num_tvs"]),                 # num_tvs
                gr.update(value=base_data["other_power"]),             # other_power
                gr.update(value=base_data["comments"]),                # comments
                gr.update(choices=[], value=[]),                       # aircons_checkboxes
                f"✅ Загружена базовая конфигурация помещения"
            ]
        
        # Ищем room с таким room_type в заказе
        if not order_id_hidden_value:
            return [gr.update() for _ in range(17)] + ["❌ Ошибка: не указан ID заказа"]
        
        order_data = await load_compose_order_data(int(order_id_hidden_value))
        if not order_data:
            return [gr.update() for _ in range(17)] + ["❌ Ошибка: не удалось загрузить данные заказа"]
        
        rooms = order_data.get("rooms", [])
        for room in rooms:
            if room.get("room_type") == config_name:
                logger.info(f"Загружена конфигурация помещения: {config_name}")
                selected_aircons = room.get("selected_aircons_for_room", [])
                return [
                    gr.update(value=room.get("area", 50)),                    # room_area
                    gr.update(value=room.get("room_type", "")),               # room_type
                    gr.update(value=room.get("installation_price", 666)),     # installation_price
                    gr.update(value=room.get("brand", "Любой")),              # brand
                    gr.update(value=room.get("wifi", False)),                 # wifi_support
                    gr.update(value=room.get("inverter", False)),             # inverter_type
                    gr.update(value=room.get("price_limit", 10000)),          # max_price
                    gr.update(value=room.get("mount_type", "Любой")),         # mount_type
                    gr.update(value=room.get("ceiling_height", 2.7)),         # ceiling_height
                    gr.update(value=room.get("illumination", "Средняя")),     # illumination
                    gr.update(value=room.get("num_people", 1)),               # num_people
                    gr.update(value=room.get("activity", "Сидячая работа")),  # activity
                    gr.update(value=room.get("num_computers", 0)),            # num_computers
                    gr.update(value=room.get("num_tvs", 0)),                  # num_tvs
                    gr.update(value=room.get("other_power", 0)),              # other_power
                    gr.update(value=room.get("comments", "")),                # comments
                    gr.update(choices=selected_aircons, value=selected_aircons),  # aircons_checkboxes
                    f"✅ Загружена конфигурация: {config_name}"
                ]
        
        # Если room с таким типом не найден, возвращаем базовую конфигурацию
        logger.warning(f"Помещение '{config_name}' не найдено, загружаем базовую конфигурацию")
        base_data = get_placeholder_room_data()
        return [
            gr.update(value=base_data["area"]),                    # room_area
            gr.update(value=config_name),                          # room_type (устанавливаем выбранное название)
            gr.update(value=base_data["installation_price"]),     # installation_price
            gr.update(value=base_data["brand"]),                   # brand
            gr.update(value=base_data["wifi"]),                    # wifi_support
            gr.update(value=base_data["inverter"]),                # inverter_type
            gr.update(value=base_data["price_limit"]),             # max_price
            gr.update(value=base_data["mount_type"]),              # mount_type
            gr.update(value=base_data["ceiling_height"]),          # ceiling_height
            gr.update(value=base_data["illumination"]),            # illumination
            gr.update(value=base_data["num_people"]),              # num_people
            gr.update(value=base_data["activity"]),                # activity
            gr.update(value=base_data["num_computers"]),           # num_computers
            gr.update(value=base_data["num_tvs"]),                 # num_tvs
            gr.update(value=base_data["other_power"]),             # other_power
            gr.update(value=base_data["comments"]),                # comments
            gr.update(choices=[], value=[]),                       # aircons_checkboxes
            f"⚠️ Помещение '{config_name}' не найдено, загружена базовая конфигурация"
        ]
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации помещения: {e}")
        return [gr.update() for _ in range(17)] + [f"❌ Ошибка: {e}"]

async def fetch_all_orders_list():
    """Получает объединенный список всех заказов"""
    try:
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            logger.warning("fetch_all_orders_list: пользователь не аутентифицирован")
            return []
        
        headers = auth_manager.get_auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/api/all_orders/", headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Ошибка при получении объединенного списка заказов: {e}")
        return []

async def load_orders_for_table():
    """Загружает заказы для отображения в таблице"""
    try:
        orders = await fetch_all_orders_list()
        
        # Сортировка по статусу
        def status_key(order):
            status_order = {
                'partially filled': 0,
                'completely filled': 1,
                'completed': 2
            }
            return (status_order.get(order.get('status'), 99), -int(order['id']))
        
        orders_sorted = sorted(orders, key=status_key)
        
        # Формирование данных для Radio (без типа заказа)
        choices = [
            f"{o['id']} | {o['client_name']} | {o.get('address', 'Адрес клиента')} | {o['created_at']} | {o['status']}"
            for o in orders_sorted
        ]
        
        return choices
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке заказов для таблицы: {e}")
        return []

async def load_selected_order_from_radio(selected_order):
    """Загружает выбранный заказ из Radio и заполняет все поля формы"""
    try:
        if not selected_order:
            # Возвращаем пустые обновления для всех полей
            empty_updates = [gr.update(visible=True, value="Пожалуйста, выберите заказ для загрузки"), gr.update(), gr.update()]
            empty_updates.extend([gr.update() for _ in range(25)])  # 25 полей формы (6 клиент + 1 room_config_dropdown + 16 помещение + 1 aircons_checkboxes + 1 order_id_hidden)
            return tuple(empty_updates)
        
        # Извлекаем ID заказа из строки (тип заказа убран из отображения)
        parts = selected_order.split("|")
        order_id = int(parts[0].strip())
        
        logger.info(f"Загружаем составной заказ ID: {order_id}")
        
        # Загружаем данные составного заказа (в new_front.py работаем только с составными заказами)
        order_data = await load_compose_order_data(order_id)
        
        if not order_data:
            error_updates = [gr.update(visible=True, value="Ошибка при загрузке данных заказа"), gr.update(), gr.update()]
            error_updates.extend([gr.update() for _ in range(25)])
            return tuple(error_updates)
        
        # Извлекаем данные из заказа (новая структура с комнатами)
        client_data = order_data.get("client_data", {})
        
        client_name = client_data.get("full_name", "")
        client_phone = client_data.get("phone", "")
        client_mail = client_data.get("email", "")
        client_address = client_data.get("address", "")
        visit_date = client_data.get("visit_date", "")    # Теперь берем из client_data
        
        # Скидка: сначала пробуем из client_data, потом fallback на старые места
        discount = client_data.get("discount")
        logger.info(f"Загрузка скидки: client_data.discount = {discount}")
        if discount is None:
            # Fallback для старых заказов - ищем в разных местах
            rooms = order_data.get("rooms", [])
            if rooms:
                discount = rooms[0].get("discount", 0)
                logger.info(f"Fallback: rooms[0].discount = {discount}")
            else:
                # Еще один fallback - из корня order_data
                discount = order_data.get("discount", 0)
                logger.info(f"Fallback: order_data.discount = {discount}")
        discount = safe_int(discount)
        logger.info(f"Итоговая скидка после safe_int: {discount}")
        
        # Загружаем конфигурации помещений из заказа
        room_configs = load_room_configurations_from_order(order_data)
        
        # Инициализируем текущую конфигурацию как базовую при загрузке заказа
        global current_room_config
        current_room_config = "Базовая конфигурация"
        
        # Для полей секции "Данные для помещения" используем базовую конфигурацию
        base_room_data = get_placeholder_room_data()
        
        # Переходим к основному интерфейсу с загруженными данными
        return (
            gr.update(visible=False, value=""),  # load_error
            gr.update(visible=False),  # load_order_screen
            gr.update(visible=True),   # main_interface
            
            # Поля данных клиента
            gr.update(value=client_name),    # client_name
            gr.update(value=client_phone),   # client_phone
            gr.update(value=client_mail),    # client_mail
            gr.update(value=client_address), # client_address
            gr.update(value=visit_date),     # visit_date
            gr.update(value=discount),       # discount
            
            # Селектор конфигурации помещения (загружаем все room_type из rooms)
            gr.update(choices=room_configs, value="Базовая конфигурация"),  # room_config_dropdown
            
            # Поля данных помещения (загружаем базовую конфигурацию)
            gr.update(value=base_room_data["area"]),                    # room_area
            gr.update(value=base_room_data["room_type"]),               # room_type
            gr.update(value=base_room_data["installation_price"]),     # installation_price
            gr.update(value=base_room_data["brand"]),                   # brand
            gr.update(value=base_room_data["wifi"]),                    # wifi_support
            gr.update(value=base_room_data["inverter"]),                # inverter_type
            gr.update(value=base_room_data["price_limit"]),             # max_price
            gr.update(value=base_room_data["mount_type"]),              # mount_type
            gr.update(value=base_room_data["ceiling_height"]),          # ceiling_height
            gr.update(value=base_room_data["illumination"]),            # illumination
            gr.update(value=base_room_data["num_people"]),              # num_people
            gr.update(value=base_room_data["activity"]),                # activity
            gr.update(value=base_room_data["num_computers"]),           # num_computers
            gr.update(value=base_room_data["num_tvs"]),                 # num_tvs
            gr.update(value=base_room_data["other_power"]),             # other_power
            gr.update(value=base_room_data["comments"]),                # comments
            
            # Подобранные кондиционеры (пустые для базовой конфигурации)
            gr.update(choices=[], value=[]),  # aircons_checkboxes
            
            # Скрытое поле ID заказа
            gr.update(value=order_id)  # order_id_hidden
        )
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке выбранного заказа: {e}")
        error_updates = [gr.update(visible=True, value=f"Ошибка: {e}"), gr.update(), gr.update()]
        error_updates.extend([gr.update() for _ in range(25)])
        return tuple(error_updates)

async def load_compose_order_data(order_id):
    """Загружает данные составного заказа"""
    try:
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            logger.warning("load_compose_order_data: пользователь не аутентифицирован")
            return None
        
        headers = auth_manager.get_auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Ошибка при загрузке составного заказа: {e}")
        return None


# === ФУНКЦИИ ДЛЯ РАБОТЫ С КЛИЕНТАМИ ===

async def save_client_data_handler(order_id_hidden_value, client_name, client_phone, client_mail, client_address, visit_date, discount):
    """Сохраняет данные клиента для заказа (по образцу save_compose_client_handler)"""
    try:
        # Проверяем авторизацию
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Ошибка: Требуется авторизация!", None
        
        # Проверяем обязательные поля
        if not client_name or not client_phone:
            return "Ошибка: Имя клиента и телефон обязательны!", None
        
        # Формируем данные клиента (ВСЕ данные клиента в одном месте)
        client_data = {
            "full_name": client_name,
            "phone": client_phone,
            "email": client_mail or "",
            "address": client_address or "",
            "visit_date": visit_date or datetime.date.today().strftime('%Y-%m-%d'),
            "discount": safe_int(discount)
        }
        logger.info(f"Сохранение скидки: исходное значение = {discount}, после safe_int = {safe_int(discount)}")
        
        # Базовые параметры заказа (пустые, так как все данные клиента теперь в client_data)
        order_params = {}
        
        # Проверяем, есть ли уже существующий заказ
        existing_order_id = None
        if order_id_hidden_value and order_id_hidden_value != "" and order_id_hidden_value != "None":
            try:
                existing_order_id = int(order_id_hidden_value)
                if existing_order_id <= 0:
                    existing_order_id = None
            except (ValueError, TypeError):
                existing_order_id = None
        
        if existing_order_id:
            # Обновляем существующий заказ
            # Сначала получаем текущие данные заказа
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as get_client:
                get_resp = await get_client.get(f"{BACKEND_URL}/api/compose_order/{existing_order_id}", headers=headers)
                get_resp.raise_for_status()
                current_order_data = get_resp.json()
                
                if "error" in current_order_data:
                    return f"Ошибка: {current_order_data['error']}", None
            
            # Обновляем только client_data и order_params, сохраняем остальные данные
            updated_order_data = current_order_data.copy()
            updated_order_data["client_data"] = client_data
            updated_order_data["order_params"] = order_params
            
            # Определяем статус: не понижаем существующий статус
            current_status = current_order_data.get("status", "draft")
            status_priority = {"draft": 1, "partially filled": 2, "completely filled": 3}
            new_status = "draft"  # Обновление данных клиента = минимум draft
            
            # Если текущий статус выше, оставляем его
            if status_priority.get(current_status, 1) > status_priority.get(new_status, 1):
                new_status = current_status
            
            payload = {
                "id": existing_order_id,
                "compose_order_data": updated_order_data,
                "status": new_status
            }
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    msg = f"Данные клиента успешно обновлены! ID: {existing_order_id}"
                    return msg, existing_order_id
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                    return f"Ошибка: {error_msg}", None
        else:
            # Создаем новый заказ (составной заказ)
            # Создаем базовую структуру составного заказа
            compose_order_data = {
                "client_data": client_data,
                "order_params": order_params,
                "airs": [],  # Пока нет кондиционеров
                "components": [],
                "comment": "Оставьте комментарий...",
                "status": "draft"
            }
            
            payload = {
                "compose_order_data": compose_order_data,
                "status": "draft"  # Только данные клиента
            }
            
            headers = auth_manager.get_auth_headers()
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    order_id = data.get("order_id")
                    msg = f"Данные клиента успешно сохранены! ID: {order_id}"
                    return msg, order_id
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                    return f"Ошибка: {error_msg}", None
                    
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных клиента: {e}", exc_info=True)
        return f"Ошибка: {e}", None

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ПОМЕЩЕНИЯМИ (ROOM) ===

async def save_room_data_handler(order_id_hidden_value, room_area, room_type, installation_price, brand, wifi_support, inverter_type, max_price, 
                                mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, comments):
    """Сохраняет данные для помещения: создает новый room или обновляет существующий"""
    global current_room_config
    try:
        if not order_id_hidden_value:
            return "Ошибка: Сначала сохраните данные клиента!", None
        
        order_id = int(order_id_hidden_value)
        
        # Подготавливаем данные помещения для будущей модели room
        room_data = {
            "order_id": order_id,
            "area": safe_float(room_area),
            "room_type": room_type,
            "installation_price": safe_float(installation_price),
            "brand": brand,
            "wifi": safe_bool(wifi_support),
            "inverter": safe_bool(inverter_type),
            "price_limit": safe_float(max_price),
            "mount_type": mount_type,
            "ceiling_height": safe_float(ceiling_height),
            "illumination": illumination,
            "num_people": safe_int(num_people),
            "activity": activity,
            "num_computers": safe_int(num_computers),
            "num_tvs": safe_int(num_tvs),
            "other_power": safe_float(other_power),
            "comments": comments or ""
        }
        
        logger.info(f"Подготовлены данные для помещения заказа {order_id}: {room_data}")
        
        # Сохраняем данные комнаты через API
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Ошибка: Требуется авторизация!", None
        
        headers = auth_manager.get_auth_headers()
        
        # Сначала получаем текущие данные составного заказа
        async with httpx.AsyncClient() as get_client:
            get_resp = await get_client.get(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
            get_resp.raise_for_status()
            current_order_data = get_resp.json()
            
            if "error" in current_order_data:
                return f"Ошибка: {current_order_data['error']}", None
        
        # Добавляем/обновляем данные комнаты в составном заказе
        updated_order_data = current_order_data.copy()
        
        # Если еще нет массива комнат, создаем его
        if "rooms" not in updated_order_data:
            updated_order_data["rooms"] = []
        
        rooms = updated_order_data["rooms"]
        room_type_to_save = room_data.get("room_type", "").strip()
        
        if current_room_config == "Базовая конфигурация":
            # Сохранение из базовой конфигурации - ВСЕГДА создаем новое помещение
            # Проверяем, есть ли уже помещение с таким названием
            existing_room_index = None
            for i, room in enumerate(rooms):
                if room.get("room_type") == room_type_to_save:
                    existing_room_index = i
                    break
            
            if existing_room_index is not None:
                # Помещение с таким названием уже существует - обновляем его
                rooms[existing_room_index] = room_data
                logger.info(f"Обновлено существующее помещение '{room_type_to_save}' (индекс {existing_room_index})")
            else:
                # Помещения с таким названием нет - добавляем новое
                rooms.append(room_data)
                logger.info(f"Добавлено новое помещение '{room_type_to_save}' в массив rooms")
        else:
            # Сохранение из уже загруженной конфигурации - обновляем существующее помещение
            room_found = False
            for i, room in enumerate(rooms):
                if room.get("room_type") == current_room_config:
                    # Если пользователь изменил название помещения, нужно проверить уникальность
                    if room_type_to_save != current_room_config:
                        # Проверяем, нет ли уже помещения с новым названием
                        name_conflict = False
                        for j, other_room in enumerate(rooms):
                            if j != i and other_room.get("room_type") == room_type_to_save:
                                name_conflict = True
                                break
                        
                        if name_conflict:
                            return f"Ошибка: Помещение с названием '{room_type_to_save}' уже существует!", None
                    
                    rooms[i] = room_data
                    room_found = True
                    logger.info(f"Обновлено помещение '{current_room_config}' → '{room_type_to_save}' (индекс {i})")
                    break
            
            if not room_found:
                logger.error(f"Не найдено помещение '{current_room_config}' для обновления!")
                return f"Ошибка: Не найдено помещение '{current_room_config}' для обновления!", None
        
        updated_order_data["rooms"] = rooms
        
        # Сохраняем обновленный заказ
        payload = {
            "id": order_id,
            "compose_order_data": updated_order_data,
            "status": "partially filled"  # Данные клиента + помещения
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("success"):
                msg = f"Данные помещения успешно сохранены для заказа #{order_id}!"
                return msg, order_id
            else:
                error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                return f"Ошибка: {error_msg}", None
        
    except Exception as e:
        error_message = f"Ошибка при сохранении данных помещения: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, order_id_hidden_value

async def save_room_data_with_dropdown_update(order_id_hidden_value, room_area, room_type, installation_price, brand, wifi_support, inverter_type, max_price, 
                                            mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, comments):
    """Сохраняет данные помещения и обновляет dropdown конфигураций"""
    global current_room_config
    try:
        room_type_to_save = room_type.strip() if room_type else ""
        
        # Сохраняем данные помещения
        save_result, order_id = await save_room_data_handler(
            order_id_hidden_value, room_area, room_type, installation_price, brand, wifi_support, inverter_type, max_price, 
            mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, comments
        )
        
        if order_id and "успешно сохранены" in save_result:
            # КРИТИЧЕСКИ ВАЖНО: Обновляем текущую конфигурацию на только что сохраненную
            if room_type_to_save:
                current_room_config = room_type_to_save
                logger.info(f"🔄 Текущая конфигурация изменена на: {current_room_config}")
            
            # Загружаем обновленные данные заказа для dropdown
            order_data = await load_compose_order_data(int(order_id))
            if order_data:
                updated_configs = load_room_configurations_from_order(order_data)
                
                # Формируем статус с информацией о смене конфигурации
                config_status = f"✅ Конфигурация переключена на: {current_room_config}"
                
                return (
                    save_result, 
                    order_id, 
                    gr.update(choices=updated_configs, value=current_room_config),  # dropdown
                    config_status  # статус конфигурации
                )
        
        # В случае ошибки возвращаем текущее состояние
        return save_result, order_id, gr.update(), "❌ Ошибка при обновлении конфигурации"
        
    except Exception as e:
        error_message = f"Ошибка при сохранении данных помещения с обновлением dropdown: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, order_id_hidden_value, gr.update(), f"❌ Ошибка: {e}"


# === ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ КП ===

async def generate_compose_kp_handler(order_id_hidden_value):
    """Генерирует КП для составного заказа (по образцу из front.py)"""
    try:
        # Проверяем авторизацию
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Ошибка: Требуется авторизация!", None
        
        order_id = int(order_id_hidden_value)
        if not order_id or order_id <= 0:
            return "Ошибка: Некорректный ID заказа!", None
    except Exception as e:
        logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
        return f"Ошибка: Некорректный ID заказа!", None
    
    try:
        payload = {"id": order_id}
        headers = auth_manager.get_auth_headers()
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BACKEND_URL}/api/generate_compose_offer/", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                logger.error(f"Ошибка от бэкенда: {data['error']}")
                return f"Ошибка: {data['error']}", None
            
            if "pdf_path" in data:
                logger.info(f"КП успешно сгенерировано для составного заказа {order_id}")
                return "КП успешно сгенерировано!", data["pdf_path"]
            else:
                return "КП сгенерировано, но файл не найден.", None
                
    except Exception as e:
        error_message = f"Ошибка при генерации КП: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, None

# === ФУНКЦИИ ДЛЯ УДАЛЕНИЯ ЗАКАЗОВ ===

async def delete_compose_order_handler(order_id_hidden_value):
    """Удаляет составной заказ (по образцу из front.py)"""
    try:
        # Проверяем авторизацию
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Ошибка: Требуется авторизация!"
        
        order_id = int(order_id_hidden_value)
        if not order_id or order_id <= 0:
            return "Ошибка: Некорректный ID заказа!"
    except Exception as e:
        logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
        return f"Ошибка: Некорректный ID заказа!"
    
    try:
        headers = auth_manager.get_auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("success"):
                logger.info(f"Составной заказ {order_id} успешно удален")
                return f"Заказ #{order_id} успешно удален!"
            else:
                error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                return f"Ошибка: {error_msg}"
                
    except Exception as e:
        logger.error(f"Ошибка при удалении заказа: {e}", exc_info=True)
        return f"Ошибка: {e}"

# === ФУНКЦИИ ДЛЯ РАБОТЫ С КОНДИЦИОНЕРАМИ ===

async def select_aircons_for_checkboxes(order_id_hidden_value):
    """Подбирает кондиционеры на основе данных текущей выбранной конфигурации помещения"""
    global current_room_config
    try:
        # Проверяем авторизацию
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return gr.update(choices=[], value=[]), "Ошибка: Требуется авторизация"
        
        if not order_id_hidden_value:
            return gr.update(choices=[], value=[]), "Ошибка: Не указан ID заказа"
        
        headers = auth_manager.get_auth_headers()
        
        # Сначала получаем данные составного заказа с комнатами
        async with httpx.AsyncClient() as get_client:
            get_resp = await get_client.get(f"{BACKEND_URL}/api/compose_order/{order_id_hidden_value}", headers=headers)
            get_resp.raise_for_status()
            order_data = get_resp.json()
            
            if "error" in order_data:
                return gr.update(choices=[], value=[]), f"Ошибка: {order_data['error']}"
        
        # Извлекаем данные текущей выбранной конфигурации для подбора кондиционеров
        rooms = order_data.get("rooms", [])
        if not rooms:
            return gr.update(choices=[], value=[]), "❌ Нет сохраненных данных помещений. Пожалуйста, сначала сохраните данные помещения!"
        
        # Находим правильное помещение для подбора кондиционеров
        room_data = None
        
        if current_room_config == "Базовая конфигурация":
            # Для базовой конфигурации используем rooms[0] или дефолтные значения
            if len(rooms) > 0:
                room_data = rooms[0]
            else:
                # Если нет сохраненных данных, используем дефолтные значения из плейсхолдера
                placeholder_data = get_placeholder_room_data()
                room_data = placeholder_data
                logger.info("Используем дефолтные данные для подбора кондиционеров (базовая конфигурация)")
        else:
            # Ищем помещение с нужным room_type
            for room in rooms:
                if room.get("room_type") == current_room_config:
                    room_data = room
                    break
            
            if not room_data:
                return gr.update(choices=[], value=[]), f"❌ Данные для конфигурации '{current_room_config}' не найдены. Пожалуйста, сначала сохраните данные помещения!"
        
        logger.info(f"Подбор кондиционеров для конфигурации: {current_room_config}")
        
        # Формируем payload для подбора кондиционеров на основе данных комнаты
        aircon_params = {
            "area": room_data.get("area", 50),
            "brand": room_data.get("brand", "Любой"),
            "wifi": room_data.get("wifi", False),
            "inverter": room_data.get("inverter", False),
            "price_limit": room_data.get("price_limit", 10000),
            "mount_type": room_data.get("mount_type", "Любой"),
            "ceiling_height": room_data.get("ceiling_height", 2.7),
            "illumination": room_data.get("illumination", "Средняя"),
            "num_people": room_data.get("num_people", 1),
            "activity": room_data.get("activity", "Средняя"),
            "num_computers": room_data.get("num_computers", 0),
            "num_tvs": room_data.get("num_tvs", 0),
            "other_power": room_data.get("other_power", 0)
        }
        
        payload = {"aircon_params": aircon_params}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BACKEND_URL}/api/select_aircons/", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                logger.error(f"Ошибка от бэкенда: {data['error']}")
                return gr.update(choices=[], value=[]), f"Ошибка: {data['error']}"
            
            aircons_list = data.get("aircons_list", [])
            
            logger.info(f"Получен ответ от API: total_count={data.get('total_count', 'N/A')}, aircons_list length={len(aircons_list)}")
            
            if isinstance(aircons_list, list) and aircons_list:
                total_count = data.get('total_count', len(aircons_list))
                
                # Формируем список для чекбоксов
                checkbox_choices = []
                for i, aircon in enumerate(aircons_list):
                    brand = aircon.get('brand', 'N/A')
                    model = aircon.get('model_name', 'N/A')
                    power = aircon.get('cooling_power_kw', 'N/A')
                    price = aircon.get('retail_price_byn', 'N/A')
                    
                    # Формат: "Бренд | имя модели | мощность в квт | стоимость"
                    choice_text = f"{brand} | {model} | {power} кВт | {price} BYN"
                    checkbox_choices.append(choice_text)
                    
                    # Логируем первые 5 кондиционеров для отладки
                    if i < 5:
                        logger.info(f"Кондиционер {i+1}: {choice_text}")
                
                logger.info(f"Подбор кондиционеров завершен успешно: найдено {total_count} вариантов, сформировано {len(checkbox_choices)} чекбоксов.")
                status_message = f"Найдено {total_count} подходящих кондиционеров. Выберите нужные:"
                
                return gr.update(choices=checkbox_choices, value=[]), status_message
            else:
                logger.info(f"Подбор кондиционеров завершен: подходящих кондиционеров не найдено.")
                return gr.update(choices=[], value=[]), "Подходящих кондиционеров не найдено."
                
    except httpx.RequestError as e:
        error_message = f"Не удалось связаться с бэкендом: {e}"
        logger.error(error_message, exc_info=True)
        return gr.update(choices=[], value=[]), error_message
    except Exception as e:
        error_message = f"Ошибка при подборе кондиционеров: {e}"
        logger.error(error_message, exc_info=True)
        return gr.update(choices=[], value=[]), error_message

async def save_selected_aircons_handler(order_id_hidden_value, selected_aircons):
    """Сохраняет выбранные кондиционеры в поле selected_aircons_for_room в JSON данных текущей конфигурации"""
    global current_room_config
    try:
        # Проверяем авторизацию
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Ошибка: Требуется авторизация"
        
        if not order_id_hidden_value:
            return "Ошибка: Не указан ID заказа"
        
        if not selected_aircons:
            return "Ошибка: Не выбраны кондиционеры для сохранения"
        
        order_id = int(order_id_hidden_value)
        headers = auth_manager.get_auth_headers()
        
        logger.info(f"Сохранение {len(selected_aircons)} выбранных кондиционеров для заказа {order_id}")
        
        # Сначала получаем текущие данные заказа
        async with httpx.AsyncClient() as get_client:
            get_resp = await get_client.get(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
            get_resp.raise_for_status()
            order_data = get_resp.json()
            
            if "error" in order_data:
                return f"Ошибка при получении данных заказа: {order_data['error']}"
        
        # Получаем данные комнат
        rooms = order_data.get("rooms", [])
        if not rooms:
            return "Ошибка: Нет данных комнаты для сохранения кондиционеров"
        
        # Находим нужную комнату для сохранения кондиционеров
        room_data = None
        room_index = 0
        
        if current_room_config == "Базовая конфигурация":
            # Для базовой конфигурации используем rooms[0]
            if len(rooms) > 0:
                room_data = rooms[0].copy()
                room_index = 0
        else:
            # Ищем комнату с нужным room_type
            for i, room in enumerate(rooms):
                if room.get("room_type") == current_room_config:
                    room_data = room.copy()
                    room_index = i
                    break
        
        if not room_data:
            return f"Ошибка: Не найдена комната для конфигурации '{current_room_config}'"
        
        room_data["selected_aircons_for_room"] = selected_aircons
        
        # Получаем существующие данные клиента из заказа
        existing_client_data = order_data.get("client_data", {})
        
        # Обновляем комнату в массиве
        updated_rooms = rooms.copy()
        updated_rooms[room_index] = room_data
        
        # Формируем данные для сохранения
        compose_order_data = {
            "client_data": existing_client_data,  # Используем существующие данные клиента
            "rooms": updated_rooms  # Обновленный массив комнат
        }
        
        # Сохраняем обновленные данные
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/api/save_compose_order/",
                json={"id": order_id, "compose_order_data": compose_order_data, "status": "partially filled"},
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                logger.info(f"Успешно сохранены {len(selected_aircons)} кондиционеров для заказа {order_id}")
                return f"✅ Сохранено {len(selected_aircons)} выбранных кондиционеров для помещения"
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                logger.error(f"Ошибка при сохранении кондиционеров: {error_msg}")
                return f"Ошибка при сохранении: {error_msg}"
        
    except Exception as e:
        error_message = f"Ошибка при сохранении кондиционеров: {e}"
        logger.error(error_message, exc_info=True)
        return error_message

# === ФУНКЦИИ ДЛЯ РАБОТЫ С КОМПЛЕКТУЮЩИМИ ===

async def load_components_for_room(order_id_hidden_value):
    """Загружает сохраненные комплектующие для помещения из текущей выбранной конфигурации"""
    global current_room_config
    try:
        if not order_id_hidden_value:
            logger.warning("Не указан ID заказа для загрузки комплектующих")
            # Возвращаем пустые значения для всех компонентов
            empty_values = []
            for _ in components_catalog_for_ui:
                empty_values.extend([False, 0, 0.0])  # selected, qty, length
            return [gr.update(visible=False), gr.update(visible=True)] + empty_values
        
        order_id = int(order_id_hidden_value)
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            logger.error("Требуется авторизация для загрузки комплектующих")
            empty_values = []
            for _ in components_catalog_for_ui:
                empty_values.extend([False, 0, 0.0])
            return [gr.update(visible=False), gr.update(visible=True)] + empty_values
        
        headers = auth_manager.get_auth_headers()
        
        # Загружаем данные заказа
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
            if resp.status_code != 200:
                logger.error(f"Ошибка загрузки заказа {order_id}: {resp.status_code}")
                empty_values = []
                for _ in components_catalog_for_ui:
                    empty_values.extend([False, 0, 0.0])
                return [gr.update(visible=False), gr.update(visible=True)] + empty_values
            
            order_data = resp.json()
            
            # Извлекаем комплектующие из текущей выбранной конфигурации
            rooms = order_data.get("rooms", [])
            saved_components = []
            
            if current_room_config == "Базовая конфигурация":
                # Для базовой конфигурации используем rooms[0]
                if rooms and len(rooms) > 0:
                    saved_components = rooms[0].get("components_for_room", [])
                    logger.info(f"Загружаем комплектующие из базовой конфигурации (rooms[0])")
            else:
                # Ищем комнату с нужным room_type
                for room in rooms:
                    if room.get("room_type") == current_room_config:
                        saved_components = room.get("components_for_room", [])
                        logger.info(f"Загружаем комплектующие из конфигурации: {current_room_config}")
                        break
            
            logger.info(f"Загружено {len(saved_components)} сохраненных комплектующих для заказа {order_id}")
            
            # Создаем словарь сохраненных компонентов для быстрого поиска
            saved_dict = {}
            for comp in saved_components:
                comp_name = comp.get("name", "")
                saved_dict[comp_name] = {
                    "selected": comp.get("selected", False),
                    "qty": comp.get("qty", 0),
                    "length": comp.get("length", 0.0)
                }
            
            # Формируем значения для UI
            component_values = []
            for component_data in components_catalog_for_ui:
                comp_name = component_data["name"]
                if comp_name in saved_dict:
                    # Используем сохраненные значения
                    saved_comp = saved_dict[comp_name]
                    component_values.extend([
                        saved_comp["selected"],
                        saved_comp["qty"],
                        saved_comp["length"]
                    ])
                else:
                    # Используем значения по умолчанию
                    component_values.extend([False, 0, 0.0])
            
            return [gr.update(visible=False), gr.update(visible=True)] + component_values
            
    except Exception as e:
        logger.error(f"Ошибка при загрузке комплектующих: {e}")
        # Возвращаем пустые значения при ошибке
        empty_values = []
        for _ in components_catalog_for_ui:
            empty_values.extend([False, 0, 0.0])
        return [gr.update(visible=False), gr.update(visible=True)] + empty_values

async def save_components_handler(order_id_hidden_value, *components_inputs):
    """Сохраняет выбранные комплектующие для текущей конфигурации помещения"""
    global current_room_config
    try:
        if not order_id_hidden_value:
            return "Ошибка: Не указан ID заказа", None
        
        order_id = int(order_id_hidden_value)
        selected_components = []
        i = 0
        processing_errors = []
        
        # Итерируемся в порядке, совпадающем с UI
        for component_data in components_catalog_for_ui:
            # Проверяем, что у нас достаточно элементов в components_inputs
            if i + 2 >= len(components_inputs):
                error_msg = f"Недостаточно элементов в components_inputs: индекс {i}, ожидается минимум {i+3}, доступно {len(components_inputs)}"
                logger.error(f"{error_msg}")
                processing_errors.append(f"Компонент '{component_data.get('name', 'Unknown')}': {error_msg}")
                continue
                
            is_selected, qty, length = components_inputs[i], components_inputs[i+1], components_inputs[i+2]
            i += 3
            
            # Учитываем ключевые слова и категорию "Кабель-каналы"
            is_measurable = (
                "труба" in component_data["name"].lower() or
                "кабель" in component_data["name"].lower() or
                "теплоизоляция" in component_data["name"].lower() or
                "шланг" in component_data["name"].lower() or
                "провод" in component_data["name"].lower() or
                component_data["category"] == "Кабель-каналы"
            )
            
            if is_selected:
                component_entry = {
                    "name": component_data["name"],
                    "category": component_data["category"],
                    "price": component_data.get("price", 0),  # Добавляем цену из каталога
                    "unit": "м." if is_measurable else "шт.",  # Добавляем единицу измерения
                    "selected": True
                }
                
                if is_measurable:
                    component_entry["length"] = safe_float(length) if length is not None else 0.0
                    component_entry["qty"] = 0
                else:
                    component_entry["qty"] = safe_int(qty) if qty is not None else 0
                    component_entry["length"] = 0.0
                
                selected_components.append(component_entry)
        
        if processing_errors:
            error_summary = f"Ошибки обработки компонентов: {'; '.join(processing_errors[:3])}"
            if len(processing_errors) > 3:
                error_summary += f" и ещё {len(processing_errors) - 3} ошибок"
            logger.error(f"{error_summary}")
            return f"Ошибка: {error_summary}", order_id
        
        # Определяем тип заказа и отправляем на соответствующий эндпоинт
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated():
            return "Ошибка: Требуется авторизация", order_id
        
        headers = auth_manager.get_auth_headers()
        async with httpx.AsyncClient() as client:
            # Проверяем, является ли заказ составным
            try:
                resp = await client.get(f"{BACKEND_URL}/api/compose_order/{order_id}", headers=headers)
                if resp.status_code == 200:
                    # Это составной заказ
                    payload = {
                        "id": order_id,
                        "components": selected_components,
                        "room_config": current_room_config,  # Добавляем информацию о текущей конфигурации
                        "status": "completely filled"
                    }
                    resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if data.get("success"):
                        msg = f"Комплектующие составного заказа успешно сохранены!"
                        return msg, order_id
                    else:
                        error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                        return f"Ошибка: {error_msg}", order_id
                else:
                    # Это обычный заказ
                    payload = {"components": selected_components, "status": "completely filled"}
                    payload["id"] = order_id
                    
                    resp = await client.post(f"{BACKEND_URL}/api/save_order/", json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if data.get("success"):
                        msg = f"Комплектующие успешно сохранены!"
                        return msg, order_id
                    else:
                        error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                        return f"Ошибка: {error_msg}", order_id
                        
            except Exception as e:
                logger.error(f"Ошибка при определении типа заказа: {e}")
                return f"Ошибка: {e}", order_id
                        
    except Exception as e:
        logger.error(f"Ошибка при сохранении комплектующих: {e}", exc_info=True)
        return f"Ошибка: {e}", order_id_hidden_value

def create_new_front_interface():
    """Создает новый интерфейс фронтенда"""
    
    with gr.Blocks(
        title="Автоматизация продаж кондиционеров", 
        theme=gr.themes.Ocean(),
        head="""
        <style>
        /* Принудительное скрытие стрелочек во всех input элементах */
        * input::-webkit-outer-spin-button,
        * input::-webkit-inner-spin-button {
            -webkit-appearance: none !important;
            margin: 0 !important;
            display: none !important;
        }
        
        * input[type=text]::-webkit-outer-spin-button,
        * input[type=text]::-webkit-inner-spin-button {
            -webkit-appearance: none !important;
            margin: 0 !important;
            display: none !important;
        }
        
        * input {
            -moz-appearance: textfield !important;
        }
        </style>
        """,
             css="""
             /* Агрессивное скрытие стрелочек для всех input полей */
             .gradio-container input::-webkit-outer-spin-button,
             .gradio-container input::-webkit-inner-spin-button,
             .gradio-container input[type="text"]::-webkit-outer-spin-button,
             .gradio-container input[type="text"]::-webkit-inner-spin-button,
             .gradio-container input[type="number"]::-webkit-outer-spin-button,
             .gradio-container input[type="number"]::-webkit-inner-spin-button,
             .gradio-container textarea::-webkit-outer-spin-button,
             .gradio-container textarea::-webkit-inner-spin-button {
                 -webkit-appearance: none !important;
                 margin: 0 !important;
                 display: none !important;
             }
             
             .gradio-container input,
             .gradio-container input[type="text"],
             .gradio-container input[type="number"],
             .gradio-container textarea {
                 -moz-appearance: textfield !important;
                 -webkit-appearance: none !important;
             }
             
             /* Дополнительное скрытие для всех input элементов */
             input::-webkit-outer-spin-button,
             input::-webkit-inner-spin-button,
             input[type="text"]::-webkit-outer-spin-button,
             input[type="text"]::-webkit-inner-spin-button {
                 -webkit-appearance: none !important;
                 margin: 0 !important;
                 display: none !important;
             }
             
             input,
             input[type="text"] {
                 -moz-appearance: textfield !important;
                 -webkit-appearance: none !important;
             }
             """
    ) as interface:
        
        # Состояния приложения
        order_state = gr.State(get_placeholder_order())
        order_id_state = gr.State(None)
        orders_table_data = gr.State([])
        
        # === ЭКРАН АВТОРИЗАЦИИ ===
        with gr.Group(visible=True) as auth_screen:
            auth_interface, auth_status_hidden = create_auth_interface()
            
            # Кнопка для перехода к основному приложению
            with gr.Row():
                auth_status = gr.Textbox(
                    label="Статус аутентификации",
                    interactive=False,
                    visible=False
                )
                # Кнопка "Проверить статус" удалена - переход происходит автоматически
        
        # === ЭКРАН ВЫБОРА ДЕЙСТВИЯ ===
        with gr.Group(visible=False) as order_selection_screen:
            gr.Markdown("# 🏢 Система формирования коммерческих предложений")
            gr.Markdown("## Выберите действие:")
            
            with gr.Row():
                create_new_order_btn = gr.Button("📝 Создание нового заказа", variant="primary", size="lg")
                load_existing_order_btn = gr.Button("📂 Загрузка заказа", variant="secondary", size="lg")
        
        # === ЭКРАН ЗАГРУЗКИ ЗАКАЗА ===
        with gr.Group(visible=False) as load_order_screen:
            gr.Markdown("# 📂 Загрузка существующего заказа")
            
            with gr.Row():
                back_to_selection_btn = gr.Button("← Назад", variant="secondary")
                refresh_orders_btn = gr.Button("🔄 Обновить список", variant="secondary")
            
            # Список заказов (как в оригинале)
            orders_radio = gr.Radio(choices=[], label="Список заказов")
            
            load_selected_btn = gr.Button("Загрузить выбранный заказ", variant="primary")
            load_error = gr.Textbox(label="Ошибки загрузки", visible=False, interactive=False)
        
        # === ОСНОВНОЙ ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ===
        with gr.Group(visible=False) as main_interface:
            # Скрытые поля для ID заказа
            order_id_hidden = gr.Number(label="ID заказа (скрытое)", visible=False)
            
            # === ОСНОВНАЯ ВКЛАДКА "ФОРМИРОВАНИЕ ЗАКАЗА" ===
            with gr.Tab("🌟 E V E R I S 🌟", id="main_order_tab"):
                
                # Выразительный заголовок
                gr.Markdown("""
                <div style="text-align: center; padding: 20px;">
                    <h1 style="color: #2E86AB; font-size: 2.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);">
                        🏢 Формирование заказа
                    </h1>
                    <p style="color: #666; font-size: 1.1em; margin-top: 10px;">
                        Создание коммерческого предложения по кондиционерам
                    </p>
                </div>
                """)
                
                # Визуальный разделитель
                gr.Markdown("---")
                
                # === БЛОК 1: ДАННЫЕ КЛИЕНТА ===
                gr.Markdown("""
                <div style="background: linear-gradient(90deg, #e3f2fd, #bbdefb); padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 5px solid #2196f3;">
                    <h2 style="margin: 0; color: #1976d2; font-size: 1.5em;">📋 ДАННЫЕ КЛИЕНТА</h2>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">Основная информация о клиенте и условиях заказа</p>
                </div>
                """)
                with gr.Row():
                    with gr.Column():
                        client_name = gr.Textbox(label="Имя клиента", value=get_placeholder_order()["client_data"]["full_name"])
                        client_phone = gr.Textbox(label="Телефон клиента", value=get_placeholder_order()["client_data"]["phone"])
                    with gr.Column():
                        client_mail = gr.Textbox(label="Email клиента", value=get_placeholder_order()["client_data"]["email"])
                        client_address = gr.Textbox(label="Адрес клиента", value=get_placeholder_order()["client_data"]["address"])
                
                with gr.Row():
                    visit_date = gr.Textbox(label="Дата визита", value=get_placeholder_order()["order_params"]["visit_date"])
                    discount = gr.Slider(0, 50, step=1, label="Скидка (%)", value=get_placeholder_order()["order_params"]["discount"])
                
                # Кнопка сохранения данных клиента
                with gr.Row():
                    save_client_btn = gr.Button("💾 Сохранить данные клиента", variant="primary", size="lg")
                
                client_save_status = gr.Textbox(label="Статус сохранения данных клиента", interactive=False, show_copy_button=False, max_lines=1, lines=1)
                
                # === БЛОК 2: ДАННЫЕ ДЛЯ ПОМЕЩЕНИЯ ===
                gr.Markdown("""
                <div style="background: linear-gradient(90deg, #e8f5e8, #c8e6c9); padding: 15px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #4caf50;">
                    <h2 style="margin: 0; color: #388e3c; font-size: 1.5em;">🏠 ДАННЫЕ ДЛЯ ПОМЕЩЕНИЯ</h2>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">Характеристики помещения и требования к кондиционированию</p>
                </div>
                """)
                
                # Селектор конфигурации помещения
                with gr.Row():
                    room_config_dropdown = gr.Dropdown(
                        choices=["Базовая конфигурация"], 
                        label="🔧 Конфигурация помещения", 
                        value="Базовая конфигурация",
                        info="Выберите существующее помещение или создайте новое",
                        scale=3
                    )
                    load_config_btn = gr.Button(
                        "🚀 Загрузить конфигурацию", 
                        variant="primary", 
                        size="lg",
                        scale=1,
                        elem_classes="config-load-btn"
                    )
                
                # Статус загрузки конфигурации
                config_load_status = gr.Textbox(label="Статус загрузки конфигурации", interactive=False, show_copy_button=False, max_lines=1, lines=1)
                
                # Важное примечание для пользователя
                gr.HTML("""
                <div style="background: #e3f2fd; border: 1px solid #90caf9; border-radius: 8px; padding: 12px; margin: 10px 0;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 18px;">💡</span>
                        <span style="color: #1565c0; font-weight: 500;">
                            Перед добавлением нового помещения к заказу обязательно загрузите базовую конфигурацию!
                        </span>
                    </div>
                </div>
                """)
                
                # Кастомные стили для кнопки загрузки конфигурации
                gr.HTML("""
                <style>
                .config-load-btn {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                    border: none !important;
                    border-radius: 12px !important;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
                    transition: all 0.3s ease !important;
                    font-weight: 600 !important;
                    text-transform: uppercase !important;
                    letter-spacing: 0.5px !important;
                }
                .config-load-btn:hover {
                    transform: translateY(-2px) !important;
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
                    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
                }
                .config-load-btn:active {
                    transform: translateY(0px) !important;
                    box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3) !important;
                }
                </style>
                """)
                
                with gr.Row():
                    room_area = gr.Slider(10, 200, step=5, label="Площадь помещения (м²)", value=get_placeholder_order()["aircon_params"]["area"])
                    room_type = gr.Textbox(
                        label="Название помещения", 
                        placeholder="Например: кухня, спальня, гостиная...", 
                        value="", 
                        show_copy_button=False, 
                        max_lines=1,
                        info="Должно быть уникальным в рамках одного заказа"
                    )
                    installation_price = gr.Slider(0, 5000, step=50, label="Стоимость монтажа (BYN)", value=get_placeholder_order()["order_params"]["installation_price"])
                
                with gr.Row():
                    brand = gr.Dropdown(["Любой", "Midea", "Dantex", "Electrolux", "Toshiba", "Hisense", "Mitsubishi", "Samsung", "TCL"], label="Бренд", value=get_placeholder_order()["aircon_params"]["brand"])
                    wifi_support = gr.Checkbox(label="Поддержка Wi-Fi", value=get_placeholder_order()["aircon_params"]["wifi"])
                    inverter_type = gr.Checkbox(label="Инверторный тип", value=get_placeholder_order()["aircon_params"]["inverter"])
                
                with gr.Row():
                    mount_type = gr.Dropdown(["Любой", "настенный", "кассетного типа", "канальный", "напольный", "потолочный", "напольно-потолочный"], label="Тип кондиционера", value=get_placeholder_order()["aircon_params"]["mount_type"])
                    ceiling_height = gr.Slider(2.0, 5.0, step=0.1, label="Высота потолков (м)", value=get_placeholder_order()["aircon_params"]["ceiling_height"])
                    max_price = gr.Slider(0, 22000, label="Верхний порог стоимости (BYN)", value=get_placeholder_order()["aircon_params"]["price_limit"])
                
                with gr.Row():
                    num_people = gr.Slider(1, 20, step=1, label="Количество людей", value=get_placeholder_order()["aircon_params"]["num_people"])
                    activity = gr.Dropdown(["Сидячая работа", "Легкая работа", "Средняя работа", "Тяжелая работа", "Спорт"], label="Активность людей", value="Сидячая работа")
                    illumination = gr.Dropdown(["Слабая", "Средняя", "Сильная"], label="Освещенность", value=get_placeholder_order()["aircon_params"]["illumination"])
                
                with gr.Row():
                    num_computers = gr.Slider(0, 10, step=1, label="Количество компьютеров", value=get_placeholder_order()["aircon_params"]["num_computers"])
                    num_tvs = gr.Slider(0, 5, step=1, label="Количество телевизоров", value=get_placeholder_order()["aircon_params"]["num_tvs"])
                    other_power = gr.Slider(0, 2000, step=50, label="Мощность прочей техники (Вт)", value=get_placeholder_order()["aircon_params"]["other_power"])
                
                # Комментарии к помещению
                comments = gr.Textbox(
                    label="💬 Комментарии к помещению",
                    placeholder="Введите дополнительные комментарии к данному помещению...",
                    lines=3,
                    max_lines=5,
                    value="Оставьте комментарий..."
                )
                
                # Кнопка сохранения данных для помещения
                with gr.Row():
                    save_room_btn = gr.Button("💾 Сохранить данные для помещения", variant="primary", size="lg")
                
                room_save_status = gr.Textbox(label="Статус сохранения данных для помещения", interactive=False, show_copy_button=False, max_lines=1, lines=1)
                
                # Визуальный разделитель после секции помещения
                gr.Markdown("---")
                gr.Markdown("")  # Дополнительный отступ
                
                # Кнопка подбора кондиционеров
                with gr.Row():
                    select_aircons_btn = gr.Button("🔍 Подобрать кондиционеры", variant="secondary", size="lg")
                
                # Примечание для пользователя
                gr.HTML("""
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 12px; margin: 10px 0;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 18px;">⚠️</span>
                        <span style="color: #856404; font-weight: 500;">
                            Пожалуйста, сохраните данные помещения перед подбором кондиционеров!
                        </span>
                    </div>
                </div>
                """)
                
                # Статус подбора кондиционеров (отдельное поле)
                aircons_selection_status = gr.Textbox(label="Статус подбора кондиционеров", interactive=False, show_copy_button=False, max_lines=1, lines=1)
                
                # Визуальный разделитель между секциями
                gr.Markdown("---")
                
                # Секция 3: Подобранные кондиционеры (чекбоксы)
                gr.Markdown("## ❄️ Подобранные кондиционеры")
                aircons_checkboxes = gr.CheckboxGroup(
                    label="Выберите кондиционеры:",
                    choices=[],
                    value=[],
                    interactive=True
                )
                
                with gr.Row():
                    save_selected_aircons_btn = gr.Button("💾 Сохранить выбранные кондиционеры", variant="primary")
                    add_components_btn = gr.Button("🔧 Добавить комплектующие", variant="secondary")
                
                aircons_save_status = gr.Textbox(label="Статус сохранения кондиционеров", interactive=False, show_copy_button=False, max_lines=1, lines=1)
                
                # === БЛОК 3: ГЕНЕРАЦИЯ КОММЕРЧЕСКОГО ПРЕДЛОЖЕНИЯ ===
                gr.Markdown("""
                <div style="background: linear-gradient(90deg, #fff3e0, #ffcc80); padding: 15px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #ff9800;">
                    <h2 style="margin: 0; color: #f57c00; font-size: 1.5em;">📄 ГЕНЕРАЦИЯ КОММЕРЧЕСКОГО ПРЕДЛОЖЕНИЯ</h2>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">Создание итогового документа с расчетами и предложением</p>
                </div>
                """)
                with gr.Row():
                    generate_kp_btn = gr.Button("📄 Сгенерировать КП", variant="primary", size="lg")
                
                # Результат генерации КП
                kp_status = gr.Textbox(label="Статус генерации КП", interactive=False, show_copy_button=False, max_lines=1, lines=1)
                pdf_output = gr.File(label="Скачать коммерческое предложение")
                
                # Визуальный разделитель
                gr.Markdown("---")
                
                # Секция управления заказом
                gr.Markdown("## ⚙️ Управление заказом")
                with gr.Row():
                    delete_order_btn = gr.Button("🗑️ Удалить заказ", variant="stop", size="sm")
                    back_to_main_btn = gr.Button("← К выбору действий", variant="secondary")
        
        # === ВСПЛЫВАЮЩАЯ ВКЛАДКА "КОМПЛЕКТУЮЩИЕ" ===
        with gr.Group(visible=False) as components_interface:
            gr.Markdown("# 🔧 Комплектующие")
            gr.Markdown("### Подбор комплектующих для монтажа")
            
            # Создаем компоненты по категориям
            components_by_category = defaultdict(list)
            unique_components = COMPONENTS_CATALOG.get("components", [])
            
            for idx, comp in enumerate(unique_components):
                components_by_category[comp["category"]].append((comp, idx))
            
            for category, components_in_cat in components_by_category.items():
                with gr.Group():
                    gr.Markdown(f"#### {category}")
                    for comp, idx in components_in_cat:
                        with gr.Row(equal_height=True):
                            with gr.Column(scale=1):
                                image_path = get_component_image_path(comp.get('image_path'))
                                gr.Image(value=image_path, label="Фото", height=80, width=80, interactive=False)
                            with gr.Column(scale=5):
                                is_measurable = ("труба" in comp["name"].lower() or 
                                               "кабель" in comp["name"].lower() or 
                                               "теплоизоляция" in comp["name"].lower() or 
                                               "шланг" in comp["name"].lower() or 
                                               "провод" in comp["name"].lower() or 
                                               comp["category"] == "Кабель-каналы")
                                label_text = f"{comp['name']}"
                                checkbox = gr.Checkbox(label=label_text)
                            with gr.Column(scale=2):
                                if is_measurable:
                                    qty_input = gr.Number(label="Кол-во (шт)", visible=False)
                                else:
                                    qty_input = gr.Number(label="Кол-во (шт)", minimum=0, step=1)
                            with gr.Column(scale=2):
                                if is_measurable:
                                    length_input = gr.Number(label="Длина (м)", minimum=0, step=1)
                                else:
                                    length_input = gr.Number(visible=False)
                            
                            # Проверяем корректность объектов Gradio
                            if (checkbox is not None and qty_input is not None and length_input is not None and
                                hasattr(checkbox, '_id') and hasattr(qty_input, '_id') and hasattr(length_input, '_id')):
                                components_ui_inputs.extend([checkbox, qty_input, length_input])
                                components_catalog_for_ui.append(comp)
            
            with gr.Row():
                save_components_btn = gr.Button("💾 Сохранить комплектующие", variant="primary")
                cancel_components_btn = gr.Button("← Назад к заказу", variant="secondary")
            
            components_save_status = gr.Textbox(label="Статус сохранения комплектующих", interactive=False, show_copy_button=False, max_lines=1, lines=1)
        
        # === ОБРАБОТЧИКИ СОБЫТИЙ ===
        
        # Проверка авторизации
        def check_authentication():
            """Проверяет статус авторизации и переключает экраны"""
            auth_manager = get_auth_manager()
            if auth_manager.is_authenticated():
                return [
                    gr.update(visible=False),  # auth_screen
                    gr.update(visible=True),   # order_selection_screen
                    gr.update(
                        visible=True, 
                        value=f"Авторизован как: {auth_manager.username}"
                    )  # auth_status
                ]
            else:
                return [
                    gr.update(visible=True),   # auth_screen
                    gr.update(visible=False),  # order_selection_screen
                    gr.update(
                        visible=True, 
                        value="Необходима авторизация"
                    )  # auth_status
                ]
        
        def handle_auth_success(auth_status_value):
            """Обрабатывает успешную аутентификацию и переключает экраны"""
            # Проверяем, если статус содержит "AUTH_SUCCESS"
            if auth_status_value == "AUTH_SUCCESS":
                auth_manager = get_auth_manager()
                return [
                    gr.update(visible=False),  # auth_screen
                    gr.update(visible=True),   # order_selection_screen
                    gr.update(
                        visible=True, 
                        value=f"✅ Авторизован как: {auth_manager.username}"
                    )  # auth_status
                ]
            else:
                return [
                    gr.update(visible=True),   # auth_screen
                    gr.update(visible=False),  # order_selection_screen
                    gr.update(
                        visible=True, 
                        value="❌ Ошибка авторизации"
                    )  # auth_status
                ]
        
        # Обработчик кнопки "Проверить статус" удален - переход происходит автоматически
        
        # Автоматическая проверка аутентификации при загрузке интерфейса
        interface.load(
            fn=check_authentication,
            outputs=[auth_screen, order_selection_screen, auth_status]
        )
        
        # Автоматическая проверка аутентификации при загрузке страницы
        # Переход происходит автоматически через check_authentication()
        
        # Обработчик для автоматического перехода после успешной аутентификации
        
        # Автоматический переход при изменении статуса аутентификации
        auth_status_hidden.change(
            fn=handle_auth_success,
            inputs=[auth_status_hidden],
            outputs=[auth_screen, order_selection_screen, auth_status]
        )
        
        # Переход к созданию нового заказа
        create_new_order_btn.click(
            fn=lambda: [gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)],
            outputs=[order_selection_screen, load_order_screen, main_interface]
        )
        
        # Переход к загрузке заказа
        async def show_load_orders():
            choices = await load_orders_for_table()
            return [
                gr.update(visible=False),  # order_selection_screen
                gr.update(visible=True),   # load_order_screen
                gr.update(visible=False),  # main_interface
                gr.update(choices=choices, value=None)  # orders_radio
            ]
        
        load_existing_order_btn.click(
            fn=show_load_orders,
            outputs=[order_selection_screen, load_order_screen, main_interface, orders_radio]
        )
        
        # Обновление списка заказов
        async def refresh_orders():
            choices = await load_orders_for_table()
            return gr.update(choices=choices, value=None)
        
        refresh_orders_btn.click(
            fn=refresh_orders,
            outputs=[orders_radio]
        )
        
        # Загрузка выбранного заказа
        load_selected_btn.click(
            fn=load_selected_order_from_radio,
            inputs=[orders_radio],
            outputs=[load_error, load_order_screen, main_interface, 
                    # Поля данных клиента
                    client_name, client_phone, client_mail, client_address, visit_date, discount,
                    # Селектор конфигурации помещения
                    room_config_dropdown,
                    # Поля данных помещения
                    room_area, room_type, installation_price, brand, wifi_support, inverter_type, max_price,
                    mount_type, ceiling_height, illumination, num_people, activity, 
                    num_computers, num_tvs, other_power, comments,
                    # Подобранные кондиционеры
                    aircons_checkboxes,
                    # Скрытое поле ID заказа
                    order_id_hidden]
        )
        
        # Возврат к выбору действий
        back_to_selection_btn.click(
            fn=lambda: [gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)],
            outputs=[order_selection_screen, load_order_screen, main_interface]
        )
        
        back_to_main_btn.click(
            fn=lambda: [gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)],
            outputs=[order_selection_screen, load_order_screen, main_interface]
        )
        
        # Загрузка выбранной конфигурации помещения
        load_config_btn.click(
            fn=load_room_config_data,
            inputs=[room_config_dropdown, order_id_hidden],
            outputs=[room_area, room_type, installation_price, brand, wifi_support, inverter_type, max_price,
                    mount_type, ceiling_height, illumination, num_people, activity, 
                    num_computers, num_tvs, other_power, comments, aircons_checkboxes, config_load_status]
        )
        
        # Показать/скрыть комплектующие с загрузкой сохраненных значений
        add_components_btn.click(
            fn=load_components_for_room,
            inputs=[order_id_hidden],
            outputs=[main_interface, components_interface] + components_ui_inputs
        )
        
        cancel_components_btn.click(
            fn=lambda: [gr.update(visible=True), gr.update(visible=False)],
            outputs=[main_interface, components_interface]
        )
        
        # Сохранение комплектующих
        save_components_btn.click(
            fn=save_components_handler,
            inputs=[order_id_hidden] + components_ui_inputs,
            outputs=[components_save_status, order_id_hidden]
        )
        
        # Подбор кондиционеров
        select_aircons_btn.click(
            fn=select_aircons_for_checkboxes,
            inputs=[order_id_hidden],
            outputs=[aircons_checkboxes, aircons_selection_status]
        )
        
        # Сохранение выбранных кондиционеров
        save_selected_aircons_btn.click(
            fn=save_selected_aircons_handler,
            inputs=[order_id_hidden, aircons_checkboxes],
            outputs=[aircons_save_status]
        )
        
        # Сохранение данных клиента
        save_client_btn.click(
            fn=save_client_data_handler,
            inputs=[order_id_hidden, client_name, client_phone, client_mail, client_address, visit_date, discount],
            outputs=[client_save_status, order_id_hidden]
        )
        
        # Сохранение данных для помещения (включая комментарии)
        save_room_btn.click(
            fn=save_room_data_with_dropdown_update,
            inputs=[order_id_hidden, room_area, room_type, installation_price, brand, wifi_support, inverter_type, max_price, 
                   mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, comments],
            outputs=[room_save_status, order_id_hidden, room_config_dropdown, config_load_status]
        )
        
        
        # Генерация КП
        generate_kp_btn.click(
            fn=generate_compose_kp_handler,
            inputs=[order_id_hidden],
            outputs=[kp_status, pdf_output]
        )
        
        # Удаление заказа
        delete_order_btn.click(
            fn=delete_compose_order_handler,
            inputs=[order_id_hidden],
            outputs=[kp_status]  # Используем kp_status для отображения результата удаления
        )
        
    return interface

# Создаем интерфейс
interface = create_new_front_interface()
