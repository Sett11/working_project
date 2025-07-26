"""
Модуль фронтенда Gradio для системы формирования коммерческих предложений по кондиционерам.
"""
import gradio as gr
import httpx
from utils.mylogger import Logger
import json
import os
from collections import defaultdict
import re
import datetime

# Инициализация логгера
logger = Logger(name=__name__, log_file="frontend.log")
BACKEND_URL = "http://backend:8000"
COMPONENTS_CATALOG_PATH = os.path.join(os.path.dirname(__file__), '../docs/components_catalog.json')
PLACEHOLDER_IMAGE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../docs/images_comp/placeholder.jpg'))

def load_components_catalog():
    try:
        with open(COMPONENTS_CATALOG_PATH, encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки каталога комплектующих: {e}")
        return {"components": []}

COMPONENTS_CATALOG = load_components_catalog()

# --- ОБНОВЛЕННАЯ ФУНКЦИЯ ДЛЯ РАБОТЫ С ПУТЯМИ ---
def get_component_image_path(image_path_from_json):
    """
    Получает абсолютный путь к изображению компонента по его относительному пути из JSON.
    """
    if not image_path_from_json:
        return PLACEHOLDER_IMAGE
    
    try:
        # Строим путь от корня проекта, где лежат папки docs, front и т.д.
        # Docker volume монтирует корень проекта в /app
        # Пример image_path_from_json: "images_comp/truba.jpg"
        # docs_path = /app/docs/
        # full_path = /app/docs/images_comp/truba.jpg
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        full_path = os.path.join(base_dir, 'docs', image_path_from_json)

        if os.path.exists(full_path):
            return full_path
        else:
            logger.warning(f"Файл изображения не найден по пути: {full_path}")
            return PLACEHOLDER_IMAGE
    except Exception as e:
        logger.error(f"Ошибка при получении изображения для {image_path_from_json}: {e}")
        return PLACEHOLDER_IMAGE

def fix_date(date_str):
    """
    Преобразует дату из DD-MM-YYYY в YYYY-MM-DD, если нужно.
    Если формат не подходит — возвращает исходное значение.
    """
    if isinstance(date_str, str) and re.match(r"^\d{2}-\d{2}-\d{4}$", date_str):
        d, m, y = date_str.split('-')
        return f"{y}-{m}-{d}"
    return date_str

# ... (функции generate_kp и select_aircons остаются без изменений) ...
async def generate_kp(client_name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type,
                ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand,
                installation_price, *components_inputs):
    logger.info(f"Получен запрос на генерацию КП для клиента: {client_name}")
    # --- Проверка обязательных полей ---
    if not client_name or not phone:
        logger.error("Имя клиента или телефон не заполнены!")
        return "Ошибка: заполните имя и телефон клиента!", None
    # --- Приведение типов ---
    try:
        area = float(area)
    except Exception:
        area = 0
    try:
        discount = int(discount)
    except Exception:
        discount = 0
    try:
        installation_price = float(installation_price)
    except Exception:
        installation_price = 0
    try:
        price = float(price)
    except Exception:
        price = 0
    try:
        ceiling_height = float(ceiling_height)
    except Exception:
        ceiling_height = 2.7
    try:
        num_people = int(num_people)
    except Exception:
        num_people = 1
    try:
        num_computers = int(num_computers)
    except Exception:
        num_computers = 0
    try:
        num_tvs = int(num_tvs)
    except Exception:
        num_tvs = 0
    try:
        other_power = float(other_power)
    except Exception:
        other_power = 0
    selected_components = []
    i = 0
    for component_data in COMPONENTS_CATALOG.get("components", []):
        is_selected = components_inputs[i]
        qty = components_inputs[i+1]
        length = components_inputs[i+2]
        i += 3
        is_measurable = "труба" in component_data["name"].lower() or "кабель" in component_data["name"].lower() or "теплоизоляция" in component_data["name"].lower() or "шланг" in component_data["name"].lower() or "провод" in component_data["name"].lower()
        if is_selected:
            comp_item = {"name": component_data["name"], "price": component_data.get("price", 0), "currency": COMPONENTS_CATALOG.get("catalog_info", {}).get("currency", "BYN")}
            if is_measurable:
                comp_item["unit"] = "м."
                comp_item["qty"] = 0
                comp_item["length"] = float(length) if length else 0.0
            else:
                comp_item["unit"] = "шт."
                comp_item["qty"] = int(qty) if qty else 0
                comp_item["length"] = 0.0
            # Добавляем только если qty > 0 или length > 0
            if comp_item["qty"] > 0 or comp_item["length"] > 0:
                selected_components.append(comp_item)
    illumination_map = {"Слабая": 0, "Средняя": 1, "Сильная": 2}
    activity_map = {"Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
    payload = {
        "client_data": {"full_name": client_name, "phone": phone, "email": mail, "address": address},
        "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": date, "installation_price": installation_price},
        "aircon_params": {"wifi": wifi, "inverter": inverter, "price_limit": price, "brand": brand, "mount_type": mount_type, "area": area, "ceiling_height": ceiling_height, "illumination": illumination_map.get(illumination, 1), "num_people": num_people, "activity": activity_map.get(activity, 0), "num_computers": num_computers, "num_tvs": num_tvs, "other_power": other_power},
        "components": selected_components
    }
    try:
        logger.info(f"Отправка запроса на эндпоинт /api/generate_offer/ на бэкенде.")
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BACKEND_URL}/api/generate_offer/", json=payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                logger.error(f"Ошибка от бэкенда: {data['error']}")
                return f"Ошибка: {data['error']}", None
            pdf_path = data.get("pdf_path", None)
            formatted_list = "Коммерческое предложение генерируется... Пожалуйста, скачайте PDF файл."
            logger.info(f"КП для клиента {client_name} успешно сформировано.")
            return formatted_list, pdf_path
    except httpx.RequestError as e:
        error_message = f"Не удалось связаться с бэкендом: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, None
    except Exception as e:
        error_message = f"Произошла внутренняя ошибка: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, None

async def select_aircons(name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type,
                   ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand):
    logger.info(f"Подбор кондиционеров для клиента: {name}")
    illumination_map = {"Слабая": 0, "Средняя": 1, "Сильная": 2}
    activity_map = {"Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
    payload = {"client_data": {"full_name": name, "phone": phone, "email": mail, "address": address}, "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": date}, "aircon_params": {"wifi": wifi, "inverter": inverter, "price_limit": price, "brand": brand, "mount_type": mount_type, "area": area, "ceiling_height": ceiling_height, "illumination": illumination_map.get(illumination, 1), "num_people": num_people, "activity": activity_map.get(activity, 0), "num_computers": num_computers, "num_tvs": num_tvs, "other_power": other_power}}
    try:
        logger.info(f"Отправка запроса на эндпоинт /api/select_aircons/ на бэкенде.")
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BACKEND_URL}/api/select_aircons/", json=payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                logger.error(f"Ошибка от бэкенда: {data['error']}")
                return f"Ошибка: {data['error']}"
            aircons_list = data.get("aircons_list", [])
            if isinstance(aircons_list, list) and aircons_list:
                formatted_list = f"Найдено {data.get('total_count', len(aircons_list))} подходящих кондиционеров:\n\n"
                for i, aircon in enumerate(aircons_list, 1):
                    formatted_list += f"{i}. {aircon.get('brand', 'N/A')} {aircon.get('model_name', 'N/A')}\n"
                    formatted_list += f"   Мощность охлаждения: {aircon.get('cooling_power_kw', 'N/A')} кВт\n"
                    formatted_list += f"   Цена: {aircon.get('retail_price_byn', 'N/A')} BYN\n"
                    formatted_list += f"   Инвертор: {'Да' if aircon.get('is_inverter') else 'Нет'}\n\n"
            else:
                formatted_list = "Подходящих кондиционеров не найдено."
            logger.info(f"Подбор кондиционеров для клиента {name} завершен успешно.")
            return formatted_list
    except httpx.RequestError as e:
        return f"Не удалось связаться с бэкендом: {e}"
    except Exception as e:
        return f"Произошла внутренняя ошибка: {e}"


# --- ГЛАВНЫЙ БЛОК ИНТЕРФЕЙСА С ИЗМЕНЕНИЯМИ ---
# --- Новый блок: Стартовый экран и логика загрузки заказа ---

# Глобальная переменная для хранения выбранного заказа (id и данные)
selected_order_id = None
loaded_order_data = {}

async def fetch_orders_list():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/api/orders/")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Ошибка при получении списка заказов: {e}")
        return []

async def fetch_order_data(order_id):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/api/order/{order_id}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Ошибка при получении заказа: {e}")
        return None

async def delete_order(order_id):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{BACKEND_URL}/api/order/{order_id}")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Ошибка при удалении заказа: {e}")
        return {"error": str(e)}

# --- PLACEHOLDER для нового заказа ---
def get_placeholder_order():
    return {
        "client_data": {
            "full_name": "Вася Плюшкин",
            "phone": "+375001111111",
            "email": "no_pain_no_gain@mail.ru",
            "address": "Минск, ул. ВесёлыхБобриков д. 89, корп. 1, кв. 99"
        },
        "order_params": {
            "room_area": 15,
            "room_type": "квартира",
            "discount": 5,
            "visit_date": datetime.date.today().strftime('%Y-%m-%d'),
            "installation_price": 666
        },
        "aircon_params": {
            "wifi": False,
            "inverter": False,
            "price_limit": 10000,  # <-- default value теперь 10000
            "brand": "Любой",
            "mount_type": "Любой",
            "area": 15,
            "ceiling_height": 2.7,
            "illumination": "Средняя",
            "num_people": 1,
            "activity": "Сидячая работа",
            "num_computers": 0,
            "num_tvs": 0,
            "other_power": 0
        },
        "components": [
            {"selected": False, "qty": 1, "length": 0.1} for _ in COMPONENTS_CATALOG.get("components", [])
        ],
        "comment": "Оставьте комментарий..."
    }

def fill_fields_from_order(order):
    client = order.get("client_data", {})
    order_params = order.get("order_params", {})
    aircon_params = order.get("aircon_params", {})
    components = order.get("components", [])
    # Собираем значения для всех input-компонентов (без комментария)
    values = [
        client.get("full_name", ""),
        client.get("phone", ""),
        client.get("email", ""),
        client.get("address", ""),
        order_params.get("visit_date", ""),
        order_params.get("room_area", 50),
        order_params.get("room_type", None),
        order_params.get("discount", 0),
        aircon_params.get("wifi", False),
        aircon_params.get("inverter", False),
        aircon_params.get("price_limit", 3000),
        aircon_params.get("mount_type", "Любой"),
        aircon_params.get("ceiling_height", 2.7),
        aircon_params.get("illumination", "Средняя"),
        aircon_params.get("num_people", 1),
        aircon_params.get("activity", "Сидячая работа"),
        aircon_params.get("num_computers", 0),
        aircon_params.get("num_tvs", 0),
        aircon_params.get("other_power", 0),
        aircon_params.get("brand", None),
        order_params.get("installation_price", 0)
    ]
    # Добавляем значения для всех комплектующих (selected, qty, length)
    for comp in components:
        values.append(comp.get("selected", False))
        values.append(comp.get("qty", 0))
        values.append(comp.get("length", 0.0))
    logger.info(f"[DEBUG] fill_fields_from_order: values count={len(values)}; values={values}")
    return [gr.update(value=v) for v in values], order.get("comment", "Оставьте комментарий...")

def fill_fields_from_order_diff(order, placeholder):
    client = order.get("client_data", {})
    order_params = order.get("order_params", {})
    aircon_params = order.get("aircon_params", {})
    components = order.get("components", [])
    ph_client = placeholder["client_data"]
    ph_order_params = placeholder["order_params"]
    ph_aircon_params = placeholder["aircon_params"]
    ph_components = placeholder["components"]
    values = [
        (client.get("full_name", ""), ph_client.get("full_name", "")),
        (client.get("phone", ""), ph_client.get("phone", "")),
        (client.get("email", ""), ph_client.get("email", "")),
        (client.get("address", ""), ph_client.get("address", "")),
        (order_params.get("visit_date", ""), ph_order_params.get("visit_date", "")),
        (order_params.get("room_area", 50), ph_order_params.get("room_area", 50)),
        (order_params.get("room_type", None), ph_order_params.get("room_type", None)),
        (order_params.get("discount", 0), ph_order_params.get("discount", 0)),
        (aircon_params.get("wifi", False), ph_aircon_params.get("wifi", False)),
        (aircon_params.get("inverter", False), ph_aircon_params.get("inverter", False)),
        (aircon_params.get("price_limit", 3000), ph_aircon_params.get("price_limit", 3000)),
        (aircon_params.get("mount_type", "Любой"), ph_aircon_params.get("mount_type", "Любой")),
        (aircon_params.get("ceiling_height", 2.7), ph_aircon_params.get("ceiling_height", 2.7)),
        (aircon_params.get("illumination", "Средняя"), ph_aircon_params.get("illumination", "Средняя")),
        (aircon_params.get("num_people", 1), ph_aircon_params.get("num_people", 1)),
        (aircon_params.get("activity", "Сидячая работа"), ph_aircon_params.get("activity", "Сидячая работа")),
        (aircon_params.get("num_computers", 0), ph_aircon_params.get("num_computers", 0)),
        (aircon_params.get("num_tvs", 0), ph_aircon_params.get("num_tvs", 0)),
        (aircon_params.get("other_power", 0), ph_aircon_params.get("other_power", 0)),
        (aircon_params.get("brand", None), ph_aircon_params.get("brand", None)),
        (order_params.get("installation_price", 0), ph_order_params.get("installation_price", 0))
    ]
    updates = []
    for v, ph in values:
        if v != ph:
            updates.append(gr.update(value=v))
        else:
            updates.append(gr.update())
    # Комплектующие — только для on_tab_change
    comp_diffs = []
    for i, comp in enumerate(components):
        ph_comp = ph_components[i] if i < len(ph_components) else {}
        for key in ["selected", "qty", "length"]:
            v = comp.get(key, False if key=="selected" else 0)
            ph_v = ph_comp.get(key, False if key=="selected" else 0)
            if v != ph_v:
                comp_diffs.append(gr.update(value=v))
            else:
                comp_diffs.append(gr.update())
    comment_value = order.get("comment", "Оставьте комментарий...")
    return updates, comp_diffs, comment_value

def update_components_tab(order_state):
    order = order_state  # order_state.value
    order_components = order.get("components", [])
    updates = []
    for catalog_comp in COMPONENTS_CATALOG.get("components", []):
        # Сравниваем имена без учёта регистра и пробелов
        cname = catalog_comp.get("name", "").replace(" ", "").lower()
        found = None
        for c in order_components:
            oname = c.get("name", "").replace(" ", "").lower()
            if cname == oname:
                found = c
                logger.info(f"[DEBUG] update_components_tab: match catalog='{catalog_comp.get('name')}' <-> order='{c.get('name')}'")
                break
        updates.append(gr.update(value=found.get("selected", False) if found else False))
        updates.append(gr.update(value=found.get("qty", 0) if found else 0))
        updates.append(gr.update(value=found.get("length", 0.0) if found else 0.0))
    logger.info(f"[DEBUG] update_components_tab: обновляю {len(updates)} полей комплектующих (по имени, нечувствительно к регистру и пробелам)")
    return updates

# --- Новый подход: управление экранами через screen_state и gr.Group(visible=...) ---

components_ui_inputs = []  # <-- ВНЕ интерфейса, глобально!

# --- Новый хелпер для подгрузки комплектующих ---
def fill_components_fields_from_order(order, components_catalog):
    """
    Возвращает список gr.update для всех полей комплектующих (чекбокс, qty, length).
    Для selected=true — значения из заказа, остальные — дефолтные.
    Порядок совпадает с components_ui_inputs.
    """
    updates = []
    order_components = order.get("components", [])
    for catalog_comp in components_catalog.get("components", []):
        # Ищем компонент в заказе по имени (без учёта регистра и пробелов)
        cname = catalog_comp.get("name", "").replace(" ", "").lower()
        found = None
        for c in order_components:
            oname = c.get("name", "").replace(" ", "").lower()
            if cname == oname:
                found = c
                break
        if found and found.get("selected"):
            updates.append(gr.update(value=True))
            updates.append(gr.update(value=found.get("qty", 0)))
            updates.append(gr.update(value=found.get("length", 0.0)))
        else:
            updates.append(gr.update(value=False))
            updates.append(gr.update(value=0))
            updates.append(gr.update(value=0.0))
    return updates

def read_notes_md():
    notes_path = os.path.join(os.path.dirname(__file__), 'notes.md')
    try:
        with open(notes_path, encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Ошибка чтения notes.md: {e}")
        return "Инструкция временно недоступна."

with gr.Blocks(title="Автоматизация продаж кондиционеров", theme=gr.themes.Ocean()) as interface:
    order_state = gr.State(get_placeholder_order())
    order_id_state = gr.State(None)  # Новый state для id заказа
    orders_table_data = gr.State([])

    with gr.Group(visible=True) as start_screen:
        gr.Markdown("<h1 style='color:#00008B;'>Everis</h1>")
        gr.Markdown("<h2 style='color:#FAEBD7;'>Cистема формирования коммерческих предложений</h2>")
        create_btn = gr.Button("Создать новый заказ", variant="primary")
        load_btn = gr.Button("Загрузить заказ", variant="secondary")
    with gr.Group(visible=False) as orders_list_screen:
        gr.Markdown("### Выберите заказ для загрузки")
        orders_radio = gr.Radio(choices=[], label="Список заказов")
        load_selected_btn = gr.Button("Загрузить выбранный заказ", variant="primary")
        load_error = gr.Markdown(visible=False)
        back_to_start_btn = gr.Button("Назад")
    with gr.Group(visible=False) as main_order_screen:
        # Вкладка "Данные для КП"
        with gr.Tab("Данные для КП"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 1. Данные клиента")
                    name = gr.Textbox(label="Имя клиента", value=get_placeholder_order()["client_data"]["full_name"])
                    phone = gr.Textbox(label="Телефон", value=get_placeholder_order()["client_data"]["phone"])
                    mail = gr.Textbox(label="Электронная почта", value=get_placeholder_order()["client_data"]["email"])
                    address = gr.Textbox(label="Адрес", value=get_placeholder_order()["client_data"]["address"])
                    date = gr.Textbox(label="Дата визита монтажника", value=get_placeholder_order()["order_params"]["visit_date"])
                with gr.Column():
                    gr.Markdown("### 2. Параметры заказа")
                    type_room = gr.Dropdown(["квартира", "дом", "офис", "производство"], label="Тип помещения", value=get_placeholder_order()["order_params"]["room_type"])
                    area = gr.Slider(10, 200, label="Площадь помещения (м²)", value=get_placeholder_order()["order_params"]["room_area"])
                    discount = gr.Slider(0, 50, label="Индивидуальная скидка (%)", value=get_placeholder_order()["order_params"]["discount"])
                    installation_price = gr.Number(label="Стоимость монтажа (BYN)", minimum=0, step=1, value=get_placeholder_order()["order_params"]["installation_price"])
            gr.Markdown("### 3. Требования к кондиционеру")
            with gr.Row():
                brand = gr.Dropdown(["Любой", "LESSAR", "DANTEX", "AUX", "QuattroClima", "Tosot", "NiceME"], label="Бренд", value=get_placeholder_order()["aircon_params"]["brand"])
                price = gr.Slider(0, 10000, value=get_placeholder_order()["aircon_params"]["price_limit"], label="Верхний порог стоимости (BYN)")
                inverter = gr.Checkbox(label="Инверторный компрессор", value=get_placeholder_order()["aircon_params"]["inverter"])
                wifi = gr.Checkbox(label="Wi-Fi управление", value=get_placeholder_order()["aircon_params"]["wifi"])
            with gr.Row():
                mount_type = gr.Dropdown(["Любой", "настенный", "кассетный", "потолочный", "напольный", "колонный"], label="Тип монтажа", value=get_placeholder_order()["aircon_params"]["mount_type"])
            gr.Markdown("### 4. Дополнительные параметры для расчета мощности")
            with gr.Row():
                ceiling_height = gr.Slider(2.0, 5.0, step=0.1, label="Высота потолков (м)", value=get_placeholder_order()["aircon_params"]["ceiling_height"])
                illumination = gr.Dropdown(["Слабая", "Средняя", "Сильная"], label="Освещенность", value=get_placeholder_order()["aircon_params"]["illumination"])
                num_people = gr.Slider(1, 10, step=1, label="Количество людей", value=get_placeholder_order()["aircon_params"]["num_people"])
                activity = gr.Dropdown(["Сидячая работа", "Легкая работа", "Средняя работа", "Тяжелая работа", "Спорт"], label="Активность людей", value=get_placeholder_order()["aircon_params"]["activity"])
            with gr.Row():
                num_computers = gr.Slider(0, 10, step=1, label="Количество компьютеров", value=get_placeholder_order()["aircon_params"]["num_computers"])
                num_tvs = gr.Slider(0, 5, step=1, label="Количество телевизоров", value=get_placeholder_order()["aircon_params"]["num_tvs"])
                other_power = gr.Slider(0, 2000, step=50, label="Мощность прочей техники (Вт)", value=get_placeholder_order()["aircon_params"]["other_power"])
            order_id_hidden = gr.Number(label="ID заказа (скрытое)", visible=False)
            # Кнопка для сохранения данных для КП
            save_kp_status = gr.Textbox(label="Статус сохранения данных для КП", interactive=False)
            save_kp_btn = gr.Button("Сохранить данные для КП", variant="primary")

        # Вкладка "Комплектующие"
        with gr.Tab("Комплектующие"):
            gr.Markdown("### Подбор комплектующих для монтажа")
            components_by_category = defaultdict(list)
            for idx, comp in enumerate(COMPONENTS_CATALOG.get("components", [])):
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
                                is_measurable = "труба" in comp["name"].lower() or "кабель" in comp["name"].lower() or "теплоизоляция" in comp["name"].lower() or "шланг" in comp["name"].lower() or "провод" in comp["name"].lower() or comp["category"] == "Кабель-каналы"
                                label_text = f"{comp['name']}"
                                checkbox = gr.Checkbox(label=label_text)
                            with gr.Column(scale=2):
                                if is_measurable:
                                    qty_input = gr.Number(label="Кол-во (шт)", visible=False)
                                else:
                                    qty_input = gr.Number(label="Кол-во (шт)", minimum=0, step=1)
                            with gr.Column(scale=2):
                                if is_measurable:
                                    length_input = gr.Number(label="Длина (м)", minimum=0, step=0.1)
                                else:
                                    length_input = gr.Number(visible=False)
                            components_ui_inputs.extend([checkbox, qty_input, length_input])
            save_components_status = gr.Textbox(label="Статус сохранения комплектующих", interactive=False)
            save_components_btn = gr.Button("Сохранить комплектующие", variant="primary")

        # Вкладка "Комментарии к заказу"
        with gr.Tab("Комментарии к заказу"):
            comment_box = gr.Textbox(label="Комментарий к заказу", value=get_placeholder_order()["comment"], lines=5, max_lines=20)
            save_comment_status = gr.Textbox(label="Статус сохранения комментария", interactive=False)
            save_comment_btn = gr.Button("Сохранить комментарий", variant="primary")

        # Вкладка "Результат" и обработчики без изменений
        with gr.Tab("Результат"):
            gr.Markdown("### Подбор кондиционеров")
            aircons_output = gr.TextArea(label="Подходящие модели", interactive=False, lines=15, max_lines=None, show_copy_button=True)
            select_aircons_btn = gr.Button("Подобрать кондиционеры", variant="primary")
            gr.Markdown("### Генерация коммерческого предложения")
            pdf_output = gr.File(label="Скачать коммерческое предложение")
            generate_btn = gr.Button("Сформировать КП", variant="primary")

        # Новая вкладка "Инструкция пользователя"
        with gr.Tab("Инструкция пользователя"):
            gr.Markdown(read_notes_md())
        
        # 1. Удаляю вкладку/группу 'Сохранить заказ' и все связанные с ней элементы
        # (Удаляю Tab/Group с save_order_status, save_order_btn, delete_order_btn)

    def show_start():
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), order_state.value, [], gr.update(value=None)
    async def show_orders():
        orders = await fetch_orders_list()
        # --- Сортировка по статусу ---
        def status_key(order):
            status_order = {
                'partially filled': 0,
                'completely filled': 1,
                'completed': 2
            }
            return (status_order.get(order.get('status'), 99), -int(order['id']))  # новые выше
        orders_sorted = sorted(orders, key=status_key)
        # --- Формирование строк ---
        choices = [
            f"{o['id']} | {o['client_name']} | {json.loads(o.get('address', '')) if False else (json.loads(o.get('address', '')) if False else (o.get('address') if o.get('address') else (json.loads(o.get('order_data', '{}')).get('client_data', {}).get('address', '') if 'order_data' in o else 'Адрес клиента')))} | {o['created_at']} | {o['status']}"
            if o.get('address') else
            f"{o['id']} | {o['client_name']} | Адрес клиента | {o['created_at']} | {o['status']}"
            for o in orders_sorted
        ]
        logger.info(f"[DEBUG] show_orders: choices={choices}")
        return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), order_state.value, gr.update(choices=choices, value=None), gr.update(visible=False, value=""), gr.update(value=None)
    async def load_selected_order(selected):
        logger.info(f"[DEBUG] load_selected_order: selected={selected}")
        if not selected:
            logger.info(f"[DEBUG] load_selected_order: error - не выбран заказ")
            return [gr.update(visible=True, value="Пожалуйста, выберите заказ для загрузки"), gr.update(visible=True), gr.update(visible=False)] + [gr.update() for _ in range(22)] + [gr.update(), gr.update(value=None)] + [gr.update() for _ in components_ui_inputs] + [gr.update(value="Оставьте комментарий..."), gr.update(value=""), gr.update(value=None), gr.update(), gr.update()]
        order_id = int(selected.split("|")[0].strip())
        order = await fetch_order_data(order_id)
        logger.info(f"[DEBUG] load_selected_order: loaded order={order}")
        placeholder = get_placeholder_order()
        updates, comp_updates, comment_value = fill_fields_from_order_diff(order, placeholder)
        comp_updates = fill_components_fields_from_order(order, COMPONENTS_CATALOG)
        # Возвращаем: ... все поля ... comment_box, save_comment_status, order_id_hidden, order_state, order_id_state
        return [gr.update(visible=False, value=""), gr.update(visible=False), gr.update(visible=True)] + updates + comp_updates + [gr.update(value=comment_value), gr.update(value=""), gr.update(value=order.get("id")), gr.update(value=order), gr.update(value=order.get("id"))]

    def show_main(order=None):
        if order is None:
            placeholder = get_placeholder_order()
            client = placeholder["client_data"]
            order_params = placeholder["order_params"]
            aircon_params = placeholder["aircon_params"]
            values = [
                gr.update(value=client.get("full_name", "")),
                gr.update(value=client.get("phone", "")),
                gr.update(value=client.get("email", "")),
                gr.update(value=client.get("address", "")),
                gr.update(value=order_params.get("visit_date", "")),
                gr.update(value=order_params.get("room_area", 50)),
                gr.update(value=order_params.get("room_type", "квартира")),
                gr.update(value=order_params.get("discount", 0)),
                gr.update(value=aircon_params.get("wifi", False)),
                gr.update(value=aircon_params.get("inverter", False)),
                gr.update(value=aircon_params.get("price_limit", 10000)),
                gr.update(value=aircon_params.get("mount_type", "Любой")),
                gr.update(value=aircon_params.get("ceiling_height", 2.7)),
                gr.update(value=aircon_params.get("illumination", "Средняя")),
                gr.update(value=aircon_params.get("num_people", 1)),
                gr.update(value=aircon_params.get("activity", "Сидячая работа")),
                gr.update(value=aircon_params.get("num_computers", 0)),
                gr.update(value=aircon_params.get("num_tvs", 0)),
                gr.update(value=aircon_params.get("other_power", 0)),
                gr.update(value=aircon_params.get("brand", "Любой")),
                gr.update(value=order_params.get("installation_price", 0)),
            ]
            for comp in placeholder["components"]:
                values.append(gr.update(value=comp.get("selected", False)))
                values.append(gr.update(value=comp.get("qty", 0)))
                values.append(gr.update(value=comp.get("length", 0.0)))
            # comment_box, save_comment_status, order_id_hidden, order_state, order_id_state
            values += [gr.update(value=placeholder.get("comment", "Оставьте комментарий...")), gr.update(value=""), gr.update(value=None), gr.update(value=placeholder), gr.update(value=None)]
            return (
                gr.update(visible=False), gr.update(visible=False), gr.update(visible=True),
                *values
            )
        else:
            updates, _ = fill_fields_from_order_diff(order, get_placeholder_order())
            comp_updates = fill_components_fields_from_order(order, COMPONENTS_CATALOG)
            comment_value = order.get("comment", "Оставьте комментарий...")
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), *updates, *comp_updates, gr.update(value=comment_value), gr.update(value=""), gr.update(value=order.get("id")), gr.update(value=order), gr.update(value=order.get("id"))

    def on_select_order(row):
        logger.info(f"[DEBUG] on_select_order: row={row}")
        if row and len(row) > 0:
            order_id = row[0]
            order = fetch_order_data(order_id)
            logger.info(f"[DEBUG] on_select_order: loaded order={order}")
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), order, orders_table_data.value
        logger.info(f"[DEBUG] on_select_order: fallback")
        return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), order_state.value, orders_table_data.value

    create_btn.click(fn=lambda: show_main(), outputs=[start_screen, orders_list_screen, main_order_screen, name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price] + components_ui_inputs + [comment_box, save_comment_status, order_id_hidden, order_state, order_id_state])
    load_btn.click(fn=show_orders, outputs=[start_screen, orders_list_screen, main_order_screen, order_state, orders_radio, load_error])
    # Собираем все input-компоненты в правильном порядке для outputs
    all_inputs = [
        name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price
    ] 

    load_selected_btn.click(
        fn=load_selected_order,
        inputs=[orders_radio],
        outputs=[load_error, orders_list_screen, main_order_screen, name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price] + components_ui_inputs + [comment_box, save_comment_status, order_id_hidden, order_state, order_id_state]
    )
    back_to_start_btn.click(fn=show_start, outputs=[start_screen, orders_list_screen, main_order_screen, order_state, orders_table_data])
    # Удаляю orders_table.select(on_select_order, outputs=[...]) как устаревший и неиспользуемый

    # --- Обработчики кнопок ---
    async def select_aircons_handler(order_id_hidden_value):
        payload = {"id": order_id_hidden_value}
        logger.info(f"[DEBUG] select_aircons_handler: payload: {json.dumps(payload, ensure_ascii=False)}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{BACKEND_URL}/api/select_aircons/", json=payload)
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    logger.error(f"Ошибка от бэкенда: {data['error']}")
                    return f"Ошибка: {data['error']}"
                aircons_list = data.get("aircons_list", [])
                if isinstance(aircons_list, list) and aircons_list:
                    formatted_list = f"Найдено {data.get('total_count', len(aircons_list))} подходящих кондиционеров:\n\n"
                    for i, aircon in enumerate(aircons_list, 1):
                        formatted_list += f"{i}. {aircon.get('brand', 'N/A')} {aircon.get('model_name', 'N/A')}\n"
                        formatted_list += f"   Мощность охлаждения: {aircon.get('cooling_power_kw', 'N/A')} кВт\n"
                        formatted_list += f"   Цена: {aircon.get('retail_price_byn', 'N/A')} BYN\n"
                        formatted_list += f"   Инвертор: {'Да' if aircon.get('is_inverter') else 'Нет'}\n\n"
                else:
                    formatted_list = "Подходящих кондиционеров не найдено."
                logger.info(f"Подбор кондиционеров завершен успешно.")
                return formatted_list
        except httpx.RequestError as e:
            error_message = f"Не удалось связаться с бэкендом: {e}"
            logger.error(error_message, exc_info=True)
            return error_message
        except Exception as e:
            error_message = f"Произошла внутренняя ошибка: {e}"
            logger.error(error_message, exc_info=True)
            return error_message

    # 3. Исправляю кнопку 'Сформировать КП' так, чтобы она отправляла только id заказа
    # и на бэкенде PDF формировался на основе данных из базы

    async def generate_kp_handler(order_id_hidden_value):
        # Отправляем только id заказа, бэкенд сам достаёт все данные и меняет статус
        payload = {"id": order_id_hidden_value}
        logger.info(f"[DEBUG] generate_kp_handler: payload: {json.dumps(payload, ensure_ascii=False)}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{BACKEND_URL}/api/generate_offer/", json=payload)
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    logger.error(f"Ошибка от бэкенда: {data['error']}")
                    return f"Ошибка: {data['error']}", None
                pdf_path = data.get("pdf_path", None)
                formatted_list = "Коммерческое предложение генерируется... Пожалуйста, скачайте PDF файл."
                logger.info(f"КП успешно сформировано.")
                return formatted_list, pdf_path
        except httpx.RequestError as e:
            error_message = f"Не удалось связаться с бэкендом: {e}"
            logger.error(error_message, exc_info=True)
            return error_message, None
        except Exception as e:
            error_message = f"Произошла внутренняя ошибка: {e}"
            logger.error(error_message, exc_info=True)
            return error_message, None

    async def save_kp_handler(
        order_id_hidden_value,
        client_name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type,
        ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price
    ):
        # Сохраняем только данные для КП (без комплектующих)
        order_id = order_id_hidden_value
        payload = {
            "client_data": {"full_name": client_name, "phone": phone, "email": mail, "address": address},
            "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": fix_date(date), "installation_price": installation_price},
            "aircon_params": {"wifi": wifi, "inverter": inverter, "price_limit": price, "brand": brand, "mount_type": mount_type, "area": area, "ceiling_height": ceiling_height, "illumination": illumination, "num_people": num_people, "activity": activity, "num_computers": num_computers, "num_tvs": num_tvs, "other_power": other_power},
            "status": "partially filled"
        }
        if order_id is not None and str(order_id).isdigit():
            payload["id"] = int(order_id)
        logger.info(f"[DEBUG] save_kp_handler: payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/save_order/", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    new_order_id = data.get("order_id")
                    msg = f"Данные для КП успешно сохранены! ID: {new_order_id}"
                    return msg, new_order_id
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                    return f"Ошибка: {error_msg}", order_id
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных для КП: {e}", exc_info=True)
            return f"Ошибка: {e}", order_id

    async def save_components_handler(
        order_id_hidden_value,
        *components_inputs
    ):
        # Сохраняем только комплектующие (по id заказа)
        order_id = order_id_hidden_value
        selected_components = []
        i = 0
        for component_data in COMPONENTS_CATALOG.get("components", []):
            is_selected, qty, length = components_inputs[i], components_inputs[i+1], components_inputs[i+2]
            i += 3
            is_measurable = "труба" in component_data["name"].lower() or "кабель" in component_data["name"].lower() or "теплоизоляция" in component_data["name"].lower() or "шланг" in component_data["name"].lower() or "провод" in component_data["name"].lower()
            comp_item = {
                "name": component_data["name"], "price": component_data.get("price", 0),
                "currency": COMPONENTS_CATALOG.get("catalog_info", {}).get("currency", "BYN"),
                "selected": is_selected
            }
            if is_measurable:
                comp_item["unit"] = "м."
                comp_item["qty"] = 0
                comp_item["length"] = float(length) if length else 0.0
            else:
                comp_item["unit"] = "шт."
                comp_item["qty"] = int(qty) if qty else 0
                comp_item["length"] = 0.0
            selected_components.append(comp_item)
        payload = {"components": selected_components, "status": "completely filled"}
        if order_id is not None and str(order_id).isdigit():
            payload["id"] = int(order_id)
        logger.info(f"[DEBUG] save_components_handler: payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/save_order/", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    msg = f"Комплектующие успешно сохранены!"
                    return msg, order_id
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                    return f"Ошибка: {error_msg}", order_id
        except Exception as e:
            logger.error(f"Ошибка при сохранении комплектующих: {e}", exc_info=True)
            return f"Ошибка: {e}", order_id

    # --- Привязка обработчиков к кнопкам ---
    select_aircons_btn.click(
        fn=select_aircons_handler,
        inputs=[order_id_hidden],
        outputs=[aircons_output]
    )

    generate_btn.click(
        fn=generate_kp_handler,
        inputs=[order_id_hidden],
        outputs=[aircons_output, pdf_output]
    )

    save_kp_btn.click(
        fn=save_kp_handler,
        inputs=[order_id_hidden, name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price],
        outputs=[save_kp_status, order_id_hidden]
    )
    save_components_btn.click(
        fn=save_components_handler,
        inputs=[order_id_hidden] + components_ui_inputs,
        outputs=[save_components_status, order_id_hidden]
    )

    async def save_comment_handler(order_id_hidden_value, comment_value):
        logger.info(f"[DEBUG] save_comment_handler: order_id_hidden_value={order_id_hidden_value}")
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID заказа!"
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return f"Ошибка: Некорректный ID заказа!"
        payload = {"id": order_id, "comment": comment_value}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/save_order/", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    return "Комментарий успешно сохранён!"
                else:
                    return f"Ошибка: {data.get('error', 'Неизвестная ошибка от бэкенда.')}"
        except Exception as e:
            logger.error(f"Ошибка при сохранении комментария: {e}", exc_info=True)
            return f"Ошибка: {e}"

    save_comment_btn.click(fn=save_comment_handler, inputs=[order_id_hidden, comment_box], outputs=[save_comment_status])