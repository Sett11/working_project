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
BACKEND_URL = "http://backend:8001"
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
    # Оставляем illumination и activity как строки, бэкенд сам преобразует
    payload = {
        "client_data": {"full_name": client_name, "phone": phone, "email": mail, "address": address},
        "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": date, "installation_price": installation_price},
        "aircon_params": {"wifi": wifi, "inverter": inverter, "price_limit": price, "brand": brand, "mount_type": mount_type, "area": area, "ceiling_height": ceiling_height, "illumination": illumination, "num_people": num_people, "activity": activity, "num_computers": num_computers, "num_tvs": num_tvs, "other_power": other_power},
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
    # Оставляем illumination и activity как строки, бэкенд сам преобразует
    payload = {"client_data": {"full_name": name, "phone": phone, "email": mail, "address": address}, "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": date}, "aircon_params": {"wifi": wifi, "inverter": inverter, "price_limit": price, "brand": brand, "mount_type": mount_type, "area": area, "ceiling_height": ceiling_height, "illumination": illumination, "num_people": num_people, "activity": activity, "num_computers": num_computers, "num_tvs": num_tvs, "other_power": other_power}}
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

async def fetch_all_orders_list():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/api/all_orders/")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Ошибка при получении объединенного списка заказов: {e}")
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
        aircon_params.get("price_limit", 10000),
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
        (aircon_params.get("price_limit", 10000), ph_aircon_params.get("price_limit", 10000)),
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
        updates.append(gr.update(value=int(found.get("qty", 0)) if found else 0))
        updates.append(gr.update(value=float(found.get("length", 0.0)) if found else 0.0))
    logger.info(f"[DEBUG] update_components_tab: обновляю {len(updates)} полей комплектующих (по имени, нечувствительно к регистру и пробелам)")
    return updates

# --- Новый подход: управление экранами через screen_state и gr.Group(visible=...) ---

components_ui_inputs = []  # <-- ВНЕ интерфейса, глобально!
# ВАЖНО: фиксируем порядок компонентов так, как он отображается в UI,
# чтобы при сохранении индексы inputs соответствовали именно этому порядку
components_catalog_for_ui = []

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
            updates.append(gr.update(value=int(found.get("qty", 0))))
            updates.append(gr.update(value=float(found.get("length", 0.0))))
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
                    area = gr.Slider(10, 160, label="Площадь помещения (м²)", value=get_placeholder_order()["order_params"]["room_area"])
                    discount = gr.Slider(0, 50, label="Индивидуальная скидка (%)", value=get_placeholder_order()["order_params"]["discount"])
                    installation_price = gr.Number(label="Стоимость монтажа (BYN)", minimum=0, step=1, value=get_placeholder_order()["order_params"]["installation_price"])
            gr.Markdown("### 3. Требования к кондиционеру")
            with gr.Row():
                brand = gr.Dropdown(["Любой", "Midea", "Dantex", "Vetero", "Electrolux", "Toshiba", "Hisense", "Mitsubishi", "Samsung", "TCL"], label="Бренд", value=get_placeholder_order()["aircon_params"]["brand"])
                price = gr.Slider(0, 22000, value=get_placeholder_order()["aircon_params"]["price_limit"], label="Верхний порог стоимости (BYN)")
                inverter = gr.Checkbox(label="Инверторный компрессор", value=get_placeholder_order()["aircon_params"]["inverter"])
                wifi = gr.Checkbox(label="Wi-Fi управление", value=get_placeholder_order()["aircon_params"]["wifi"])
            with gr.Row():
                mount_type = gr.Dropdown(["Любой", "настенный", "кассетного типа", "потолочный", "напольный", "колонный"], label="Тип монтажа", value=get_placeholder_order()["aircon_params"]["mount_type"])
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
                                    length_input = gr.Number(label="Длина (м)", minimum=0, step=0.1 if comp["category"] != "Теплоизоляция" else 2)
                                else:
                                    length_input = gr.Number(visible=False)
                            components_ui_inputs.extend([checkbox, qty_input, length_input])
                            # Фиксируем порядок каталога, соответствующий UI
                            components_catalog_for_ui.append(comp)
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
            gr.Markdown("### Управление заказом")
            delete_btn = gr.Button("Удалить заказ", variant="stop", size="sm")

        # Вкладка "Формирование специального заказа"
        with gr.Tab("Формирование составного заказа"):
            # Секция 1: Данные клиента
            gr.Markdown("## 📋 Данные клиента")
            with gr.Row():
                with gr.Column():
                    compose_name = gr.Textbox(label="Имя клиента", value=get_placeholder_order()["client_data"]["full_name"])
                    compose_phone = gr.Textbox(label="Телефон", value=get_placeholder_order()["client_data"]["phone"])
                    compose_mail = gr.Textbox(label="Электронная почта", value=get_placeholder_order()["client_data"]["email"])
                with gr.Column():
                    compose_address = gr.Textbox(label="Адрес", value=get_placeholder_order()["client_data"]["address"])
                    compose_date = gr.Textbox(label="Дата визита монтажника", value=get_placeholder_order()["order_params"]["visit_date"])
                    compose_discount = gr.Slider(0, 50, label="Индивидуальная скидка (%)", value=get_placeholder_order()["order_params"]["discount"])
            
            # Разделитель между секциями
            gr.Markdown("---")
            
            # Секция 2: Данные для подбора кондиционера
            gr.Markdown("## ❄️ Данные для подбора кондиционера")
            
            gr.Markdown("### Параметры помещения")
            with gr.Row():
                compose_type_room = gr.Textbox(label="Тип помещения", value=get_placeholder_order()["order_params"]["room_type"])
                compose_area = gr.Slider(10, 160, label="Площадь помещения (м²)", value=get_placeholder_order()["order_params"]["room_area"])
                compose_installation_price = gr.Number(label="Стоимость монтажа (BYN)", minimum=0, step=1, value=get_placeholder_order()["order_params"]["installation_price"])
            
            gr.Markdown("### Требования к кондиционеру")
            with gr.Row():
                compose_brand = gr.Dropdown(["Любой", "Midea", "Dantex", "Vetero", "Electrolux", "Toshiba", "Hisense", "Mitsubishi", "Samsung", "TCL"], label="Бренд", value=get_placeholder_order()["aircon_params"]["brand"])
                compose_price = gr.Slider(0, 22000, value=get_placeholder_order()["aircon_params"]["price_limit"], label="Верхний порог стоимости (BYN)")
                compose_inverter = gr.Checkbox(label="Инверторный компрессор", value=get_placeholder_order()["aircon_params"]["inverter"])
                compose_wifi = gr.Checkbox(label="Wi-Fi управление", value=get_placeholder_order()["aircon_params"]["wifi"])
            with gr.Row():
                compose_mount_type = gr.Dropdown(["Любой", "настенный", "кассетного типа", "потолочный", "напольный", "колонный"], label="Тип монтажа", value=get_placeholder_order()["aircon_params"]["mount_type"])
            
            gr.Markdown("### Дополнительные параметры для расчета мощности")
            with gr.Row():
                compose_ceiling_height = gr.Slider(2.0, 5.0, step=0.1, label="Высота потолков (м)", value=get_placeholder_order()["aircon_params"]["ceiling_height"])
                compose_illumination = gr.Dropdown(["Слабая", "Средняя", "Сильная"], label="Освещенность", value=get_placeholder_order()["aircon_params"]["illumination"])
                compose_num_people = gr.Slider(1, 10, step=1, label="Количество людей", value=get_placeholder_order()["aircon_params"]["num_people"])
                compose_activity = gr.Dropdown(["Сидячая работа", "Легкая работа", "Средняя работа", "Тяжелая работа", "Спорт"], label="Активность людей", value=get_placeholder_order()["aircon_params"]["activity"])
            with gr.Row():
                compose_num_computers = gr.Slider(0, 10, step=1, label="Количество компьютеров", value=get_placeholder_order()["aircon_params"]["num_computers"])
                compose_num_tvs = gr.Slider(0, 5, step=1, label="Количество телевизоров", value=get_placeholder_order()["aircon_params"]["num_tvs"])
                compose_other_power = gr.Slider(0, 2000, step=50, label="Мощность прочей техники (Вт)", value=get_placeholder_order()["aircon_params"]["other_power"])
            
            compose_order_id_hidden = gr.Number(label="ID составного заказа (скрытое)", visible=False)
            compose_save_status = gr.Textbox(label="Статус сохранения данных", interactive=False)
            compose_save_btn = gr.Button("Сохранить данные", variant="primary")
            
            # Окно отображения подобранных кондиционеров
            compose_aircons_output = gr.TextArea(label="Подходящие модели", interactive=False, lines=10, max_lines=None, show_copy_button=True)
            compose_select_btn = gr.Button("Подобрать", variant="primary")
            compose_add_aircon_btn = gr.Button("Ввести данные для следующего кондиционера", variant="secondary")
            
            # Кнопка генерации КП
            compose_generate_kp_btn = gr.Button("Сгенерировать КП", variant="primary")
            compose_kp_status = gr.Textbox(label="Статус генерации КП", interactive=False)
            compose_pdf_output = gr.File(label="Скачать коммерческое предложение")

        # Вкладка "Инструкция пользователя"
        with gr.Tab("Инструкция пользователя"):
            gr.Markdown(read_notes_md())
        
        # 1. Удаляю вкладку/группу 'Сохранить заказ' и все связанные с ней элементы
        # (Удаляю Tab/Group с save_order_status, save_order_btn, delete_order_btn)

    def show_start():
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), order_state.value, [], gr.update(value=None)
    async def show_orders():
        orders = await fetch_all_orders_list()  # Используем новый эндпоинт
        # --- Сортировка по статусу ---
        def status_key(order):
            status_order = {
                'partially filled': 0,
                'completely filled': 1,
                'completed': 2
            }
            return (status_order.get(order.get('status'), 99), -int(order['id']))  # новые выше
        orders_sorted = sorted(orders, key=status_key)
        # --- Формирование строк с типом заказа ---
        choices = [
            f"{o['id']} | {o.get('order_type', 'Order')} | {o['client_name']} | {o.get('address', 'Адрес клиента')} | {o['created_at']} | {o['status']}"
            for o in orders_sorted
        ]
        logger.info(f"[DEBUG] show_orders: choices={choices}")
        return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), order_state.value, gr.update(choices=choices, value=None), gr.update(visible=False, value=""), gr.update(value=None)
    async def load_selected_order(selected):
        logger.info(f"[DEBUG] load_selected_order: selected={selected}")
        if not selected:
            logger.info(f"[DEBUG] load_selected_order: error - не выбран заказ")
            return [gr.update(visible=True, value="Пожалуйста, выберите заказ для загрузки"), gr.update(visible=True), gr.update(visible=False)] + [gr.update() for _ in range(22)] + [gr.update() for _ in components_ui_inputs] + [gr.update(value="Оставьте комментарий..."), gr.update(value=""), gr.update(value=None), gr.update(), gr.update()] + [gr.update() for _ in range(22)] + [gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")]
        
        # Извлекаем ID и тип заказа из строки
        parts = selected.split("|")
        order_id = int(parts[0].strip())
        order_type = parts[1].strip() if len(parts) > 1 else "Order"
        
        logger.info(f"[DEBUG] load_selected_order: order_id={order_id}, order_type={order_type}")
        
        if order_type == "Compose":
            # Загружаем составной заказ
            return await load_compose_order(order_id)
        else:
            # Загружаем обычный заказ
            order = await fetch_order_data(order_id)
            logger.info(f"[DEBUG] load_selected_order: loaded order={order}")
            placeholder = get_placeholder_order()
            updates, comp_updates, comment_value = fill_fields_from_order_diff(order, placeholder)
            comp_updates = fill_components_fields_from_order(order, COMPONENTS_CATALOG)
            # Возвращаем: load_error(1), orders_list_screen(1), main_order_screen(1), обычные_поля(22), components, comment(5), compose_поля(22), compose_статусы(4)
            return [gr.update(visible=False, value=""), gr.update(visible=False), gr.update(visible=True)] + updates + comp_updates + [gr.update(value=comment_value), gr.update(value=""), gr.update(value=order.get("id")), gr.update(value=order), gr.update(value=order.get("id"))] + [gr.update() for _ in range(22)] + [gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")]

    async def load_compose_order(order_id):
        """Загружает составной заказ в вкладку 'Формирование составного заказа'"""
        logger.info(f"[DEBUG] load_compose_order: order_id={order_id}")
        
        try:
            # Получаем данные составного заказа
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BACKEND_URL}/api/compose_order/{order_id}")
                resp.raise_for_status()
                compose_order_data = resp.json()
            
            logger.info(f"[DEBUG] load_compose_order: loaded compose_order_data={compose_order_data}")
            
            if "error" in compose_order_data:
                return [gr.update(visible=True, value=f"Ошибка: {compose_order_data['error']}"), gr.update(visible=True), gr.update(visible=False)] + [gr.update() for _ in range(21)] + [gr.update() for _ in components_ui_inputs] + [gr.update(value="Оставьте комментарий..."), gr.update(value=""), gr.update(value=None), gr.update(), gr.update()] + [gr.update() for _ in range(21)] + [gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")]
            
            # Извлекаем данные клиента и скидку
            client_data = compose_order_data.get("client_data", {})
            # Извлекаем данные из последнего кондиционера
            airs = compose_order_data.get("airs", [])
            last_air = airs[-1] if airs else {}
            last_air_order_params = last_air.get("order_params", {})
            last_air_aircon_params = last_air.get("aircon_params", {})
            
            logger.info(f"[DEBUG] load_compose_order: last_air_order_params={last_air_order_params}")
            logger.info(f"[DEBUG] load_compose_order: last_air_aircon_params={last_air_aircon_params}")
            
            # Безопасное преобразование типов
            def safe_float(value):
                if value is None or value == "":
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            
            def safe_int(value):
                if value is None or value == "":
                    return 0
                try:
                    return int(float(value))  # Сначала float, потом int для случаев типа "15.0"
                except (ValueError, TypeError):
                    return 0
            
            def safe_bool(value):
                if value is None or value == "":
                    return False
                try:
                    return bool(value)
                except (ValueError, TypeError):
                    return False
            
            # ИСПРАВЛЯЕМ порядок полей для составного заказа согласно outputs строка 804:
            # compose_name, compose_phone, compose_mail, compose_address, compose_date, compose_discount, 
            # compose_area, compose_type_room, compose_wifi, compose_inverter, compose_price, compose_mount_type, 
            # compose_ceiling_height, compose_illumination, compose_num_people, compose_activity, compose_num_computers, 
            # compose_num_tvs, compose_other_power, compose_brand, compose_installation_price
            compose_fields_updates = [
                gr.update(value=client_data.get("full_name", "")),  # 1. compose_name
                gr.update(value=client_data.get("phone", "")),      # 2. compose_phone
                gr.update(value=client_data.get("email", "")),      # 3. compose_mail
                gr.update(value=client_data.get("address", "")),    # 4. compose_address
                gr.update(value=last_air_order_params.get("visit_date", "")),  # 5. compose_date
                gr.update(value=safe_int(last_air_order_params.get("discount", 0))),   # 6. compose_discount
                gr.update(value=safe_float(last_air_aircon_params.get("area", 50))),      # 7. compose_area
                gr.update(value=last_air_order_params.get("room_type", "")),      # 8. compose_type_room
                gr.update(value=safe_bool(last_air_aircon_params.get("wifi", False))),   # 9. compose_wifi
                gr.update(value=safe_bool(last_air_aircon_params.get("inverter", False))),   # 10. compose_inverter
                gr.update(value=safe_float(last_air_aircon_params.get("price_limit", 10000))),   # 11. compose_price
                gr.update(value=last_air_aircon_params.get("mount_type", "Любой")), # 12. compose_mount_type
                gr.update(value=safe_float(last_air_aircon_params.get("ceiling_height", 2.7))),     # 13. compose_ceiling_height
                gr.update(value=last_air_aircon_params.get("illumination", "Средняя")), # 14. compose_illumination
                gr.update(value=safe_int(last_air_aircon_params.get("num_people", 1))),       # 15. compose_num_people
                gr.update(value=last_air_aircon_params.get("activity", "Сидячая работа")), # 16. compose_activity
                gr.update(value=safe_int(last_air_aircon_params.get("num_computers", 0))),       # 17. compose_num_computers
                gr.update(value=safe_int(last_air_aircon_params.get("num_tvs", 0))),       # 18. compose_num_tvs
                gr.update(value=safe_float(last_air_aircon_params.get("other_power", 0))),       # 19. compose_other_power
                gr.update(value=last_air_aircon_params.get("brand", "Любой")), # 20. compose_brand
                gr.update(value=safe_float(last_air_order_params.get("installation_price", 0))),       # 21. compose_installation_price
            ]
            
            # Загружаем комплектующие
            components = compose_order_data.get("components", [])
            comp_updates = fill_components_fields_from_order({"components": components}, COMPONENTS_CATALOG)
            
            # Загружаем комментарий
            comment_value = compose_order_data.get("comment", "Оставьте комментарий...")
            logger.info(f"[DEBUG] load_compose_order: comment_value={comment_value}")
            
            # Возвращаем обновления в правильном порядке согласно outputs
            # Формат: [load_error(1), orders_list_screen(1), main_order_screen(1), обычные_поля(22), components, comment(5), compose_поля(22), compose_статусы(4)]
            
            # Отладочная информация
            logger.info(f"[DEBUG] load_compose_order: compose_fields_updates length: {len(compose_fields_updates)}")
            logger.info(f"[DEBUG] load_compose_order: comp_updates length: {len(comp_updates)}")
            logger.info(f"[DEBUG] load_compose_order: client_data: {client_data}")
            logger.info(f"[DEBUG] load_compose_order: compose_fields_updates[0]: {compose_fields_updates[0]}")
            logger.info(f"[DEBUG] load_compose_order: compose_fields_updates[1]: {compose_fields_updates[1]}")
            logger.info(f"[DEBUG] load_compose_order: compose_fields_updates[0].value: {getattr(compose_fields_updates[0], 'value', 'N/A')}")
            logger.info(f"[DEBUG] load_compose_order: compose_fields_updates[1].value: {getattr(compose_fields_updates[1], 'value', 'N/A')}")
            
            result = [
                gr.update(visible=False, value=""),  # load_error
                gr.update(visible=False),            # orders_list_screen
                gr.update(visible=True),             # main_order_screen (показываем основную страницу)
            ] + [gr.update() for _ in range(21)] + comp_updates + [
                gr.update(value=comment_value),      # comment
                gr.update(value=""),                 # save_comment_status
                gr.update(value=order_id),           # order_id_hidden
                gr.update(value=compose_order_data), # order_state
                gr.update(value=order_id),           # order_id_state
            ] + compose_fields_updates + [
                gr.update(value=""),                 # compose_save_status
                gr.update(value=order_id),           # compose_order_id_hidden
                gr.update(value=""),                 # compose_aircons_output
                gr.update(value=""),                 # compose_kp_status
            ]
            
            logger.info(f"[DEBUG] load_compose_order: total result length: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке составного заказа: {e}", exc_info=True)
            return [gr.update(visible=True, value=f"Ошибка при загрузке составного заказа: {e}"), gr.update(visible=True), gr.update(visible=False)] + [gr.update() for _ in range(21)] + [gr.update() for _ in components_ui_inputs] + [gr.update(value="Оставьте комментарий..."), gr.update(value=""), gr.update(value=None), gr.update(), gr.update()] + [gr.update() for _ in range(21)] + [gr.update(value=""), gr.update(value=None), gr.update(value=""), gr.update(value="")]

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
        outputs=[load_error, orders_list_screen, main_order_screen, name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price] + components_ui_inputs + [comment_box, save_comment_status, order_id_hidden, order_state, order_id_state, compose_name, compose_phone, compose_mail, compose_address, compose_date, compose_discount, compose_area, compose_type_room, compose_wifi, compose_inverter, compose_price, compose_mount_type, compose_ceiling_height, compose_illumination, compose_num_people, compose_activity, compose_num_computers, compose_num_tvs, compose_other_power, compose_brand, compose_installation_price, compose_save_status, compose_order_id_hidden, compose_aircons_output, compose_kp_status]
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
        # Оставляем illumination и activity как строки, бэкенд сам преобразует
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
        # Итерируемся в порядке, совпадающем с UI
        for component_data in components_catalog_for_ui if len(components_catalog_for_ui) == len(COMPONENTS_CATALOG.get("components", [])) else COMPONENTS_CATALOG.get("components", []):
            is_selected, qty, length = components_inputs[i], components_inputs[i+1], components_inputs[i+2]
            i += 3
            # Учитываем ключевые слова и категорию "Кабель-каналы"
            is_measurable = (
                "труба" in component_data["name"].lower() or
                "кабель" in component_data["name"].lower() or
                "теплоизоляция" in component_data["name"].lower() or
                "шланг" in component_data["name"].lower() or
                "провод" in component_data["name"].lower() or
                component_data.get("category") == "Кабель-каналы"
            )
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
            # Подробное логирование для проверки корректного сопоставления и сохранения
            try:
                logger.info(
                    f"[DEBUG] save_components_handler item: name='{comp_item['name']}', category='{component_data.get('category')}', "
                    f"is_measurable={is_measurable}, selected={is_selected}, unit='{comp_item['unit']}', "
                    f"qty={comp_item['qty']}, length={comp_item['length']}"
                )
            except Exception:
                pass
            selected_components.append(comp_item)
        
        # Определяем тип заказа и отправляем на соответствующий эндпоинт
        try:
            # Сначала получаем информацию о заказе
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BACKEND_URL}/api/all_orders/")
                resp.raise_for_status()
                orders = resp.json()
                
                # Ищем заказ по ID
                order_info = None
                for order in orders:
                    if order.get('id') == order_id:
                        order_info = order
                        break
                
                if not order_info:
                    return f"Ошибка: Заказ с ID {order_id} не найден", order_id
                
                order_type = order_info.get('order_type', 'Order')
                logger.info(f"[DEBUG] save_components_handler: order_type={order_type}")
                
                if order_type == 'Compose':
                    # Для составного заказа используем специальный эндпоинт
                    payload = {
                        "id": order_id,
                        "components": selected_components,
                        "status": "completely filled"
                    }
                    logger.info(f"[DEBUG] save_components_handler (compose): payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
                    
                    resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("success"):
                        msg = f"Комплектующие составного заказа успешно сохранены!"
                        return msg, order_id
                    else:
                        error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                        return f"Ошибка: {error_msg}", order_id
                else:
                    # Для обычного заказа используем стандартный эндпоинт
                    payload = {"components": selected_components, "status": "completely filled"}
                    if order_id is not None and str(order_id).isdigit():
                        payload["id"] = int(order_id)
                    logger.info(f"[DEBUG] save_components_handler (regular): payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
                    
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

    # --- Обработчики для составного заказа ---
    async def save_compose_order_handler(order_id_hidden_value, client_name, client_phone, client_mail, client_address, visit_date, 
                                       room_area, room_type, discount, wifi, inverter, price_limit, mount_type, 
                                       ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price):
        """Обработчик сохранения данных составного заказа"""
        logger.info(f"[DEBUG] save_compose_order_handler: order_id_hidden_value={order_id_hidden_value}")
        logger.info(f"[DEBUG] save_compose_order_handler: room_area={room_area} (type: {type(room_area)})")
        logger.info(f"[DEBUG] save_compose_order_handler: discount={discount} (type: {type(discount)})")
        logger.info(f"[DEBUG] save_compose_order_handler: price_limit={price_limit} (type: {type(price_limit)})")
        logger.info(f"[DEBUG] save_compose_order_handler: ceiling_height={ceiling_height} (type: {type(ceiling_height)})")
        logger.info(f"[DEBUG] save_compose_order_handler: num_people={num_people} (type: {type(num_people)})")
        logger.info(f"[DEBUG] save_compose_order_handler: num_computers={num_computers} (type: {type(num_computers)})")
        logger.info(f"[DEBUG] save_compose_order_handler: num_tvs={num_tvs} (type: {type(num_tvs)})")
        logger.info(f"[DEBUG] save_compose_order_handler: other_power={other_power} (type: {type(other_power)})")
        logger.info(f"[DEBUG] save_compose_order_handler: installation_price={installation_price} (type: {type(installation_price)})")
        
        # Проверка обязательных полей
        if not client_name or not client_phone:
            logger.error("Имя клиента или телефон не заполнены!")
            return "Ошибка: заполните имя и телефон клиента!", None
        
        try:
            # Формируем данные для сохранения
            client_data = {
                "full_name": client_name,
                "phone": client_phone,
                "email": client_mail or "",
                "address": client_address or ""
            }
            
            # Безопасное преобразование типов
            def safe_float(value):
                if value is None or value == "":
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            
            def safe_int(value):
                if value is None or value == "":
                    return 0
                try:
                    return int(float(value))  # Сначала float, потом int для случаев типа "15.0"
                except (ValueError, TypeError):
                    return 0
            
            def safe_bool(value):
                if value is None or value == "":
                    return False
                try:
                    return bool(value)
                except (ValueError, TypeError):
                    return False
            
            order_params = {
                "visit_date": visit_date,
                "room_area": safe_float(room_area),
                "room_type": room_type,
                "discount": safe_int(discount),
                "installation_price": safe_float(installation_price)
            }
            
            aircon_params = {
                "area": safe_float(room_area),
                "ceiling_height": safe_float(ceiling_height) if ceiling_height else 2.7,
                "illumination": illumination,
                "num_people": safe_int(num_people) if num_people else 1,
                "activity": activity,
                "num_computers": safe_int(num_computers),
                "num_tvs": safe_int(num_tvs),
                "other_power": safe_float(other_power),
                "brand": brand,
                "price_limit": safe_float(price_limit) if price_limit else 22000,
                "inverter": safe_bool(inverter),
                "wifi": safe_bool(wifi),
                "mount_type": mount_type
            }
            
            # Проверяем, есть ли уже существующий заказ
            if order_id_hidden_value and str(order_id_hidden_value).isdigit():
                order_id = int(order_id_hidden_value)
                # Для существующего заказа обновляем только последний кондиционер
                payload = {
                    "id": order_id,
                    "update_last_aircon": {
                        "order_params": order_params,
                        "aircon_params": aircon_params
                    },
                    "status": "partially filled"
                }
            else:
                # Для нового заказа создаем первый кондиционер
                first_air = {
                    "id": 1,
                    "order_params": order_params,
                    "aircon_params": aircon_params
                }
                
                compose_order_data = {
                    "client_data": client_data,
                    "airs": [first_air],  # Сразу добавляем первый кондиционер
                    "components": [],
                    "comment": "Оставьте комментарий...",  # Добавляем поле комментария
                    "status": "partially filled"  # Изменяем статус на partially filled
                }
                
                payload = {
                    "compose_order_data": compose_order_data,
                    "status": "partially filled"  # Изменяем статус на partially filled
                }
            
            logger.info(f"[DEBUG] save_compose_order_handler: payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/save_compose_order/", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    order_id = data.get("order_id")
                    msg = f"Данные составного заказа успешно сохранены! ID: {order_id}"
                    return msg, order_id
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                    return f"Ошибка: {error_msg}", order_id_hidden_value
                    
        except Exception as e:
            logger.error(f"Ошибка при сохранении составного заказа: {e}", exc_info=True)
            return f"Ошибка: {e}", order_id_hidden_value

    async def select_compose_aircons_handler(order_id_hidden_value):
        """Обработчик подбора кондиционеров для составного заказа"""
        logger.info(f"[DEBUG] select_compose_aircons_handler: order_id_hidden_value={order_id_hidden_value}")
        
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID составного заказа!"
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return f"Ошибка: Некорректный ID составного заказа!"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/select_compose_aircons/", json={"id": order_id})
                resp.raise_for_status()
                data = resp.json()
                
                if "error" in data:
                    return f"Ошибка: {data['error']}"
                
                # Возвращаем готовый текст результата
                return data.get("result_text", "Результаты подбора кондиционеров не найдены")
                
        except Exception as e:
            logger.error(f"Ошибка при подборе кондиционеров для составного заказа: {e}", exc_info=True)
            return f"Ошибка: {e}"

    async def add_next_aircon_handler(order_id_hidden_value, client_name, client_phone, client_mail, client_address, visit_date, 
                                    room_area, room_type, discount, wifi, inverter, price_limit, mount_type, 
                                    ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand, installation_price):
        """Обработчик добавления следующего кондиционера"""
        logger.info(f"[DEBUG] add_next_aircon_handler: order_id_hidden_value={order_id_hidden_value}")
        logger.info(f"[DEBUG] add_next_aircon_handler: room_area={room_area} (type: {type(room_area)})")
        logger.info(f"[DEBUG] add_next_aircon_handler: discount={discount} (type: {type(discount)})")
        logger.info(f"[DEBUG] add_next_aircon_handler: price_limit={price_limit} (type: {type(price_limit)})")
        logger.info(f"[DEBUG] add_next_aircon_handler: ceiling_height={ceiling_height} (type: {type(ceiling_height)})")
        logger.info(f"[DEBUG] add_next_aircon_handler: num_people={num_people} (type: {type(num_people)})")
        logger.info(f"[DEBUG] add_next_aircon_handler: num_computers={num_computers} (type: {type(num_computers)})")
        logger.info(f"[DEBUG] add_next_aircon_handler: num_tvs={num_tvs} (type: {type(num_tvs)})")
        logger.info(f"[DEBUG] add_next_aircon_handler: other_power={other_power} (type: {type(other_power)})")
        logger.info(f"[DEBUG] add_next_aircon_handler: installation_price={installation_price} (type: {type(installation_price)})")
        
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID составного заказа!", None
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return f"Ошибка: Некорректный ID составного заказа!", None
        
        try:
            # Безопасное преобразование типов
            def safe_float(value):
                if value is None or value == "":
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            
            def safe_int(value):
                if value is None or value == "":
                    return 0
                try:
                    return int(float(value))  # Сначала float, потом int для случаев типа "15.0"
                except (ValueError, TypeError):
                    return 0
            
            def safe_bool(value):
                if value is None or value == "":
                    return False
                try:
                    return bool(value)
                except (ValueError, TypeError):
                    return False
            
            # Формируем данные нового кондиционера
            aircon_params = {
                "area": safe_float(room_area),
                "ceiling_height": safe_float(ceiling_height) if ceiling_height else 2.7,
                "illumination": illumination,
                "num_people": safe_int(num_people) if num_people else 1,
                "activity": activity,
                "num_computers": safe_int(num_computers),
                "num_tvs": safe_int(num_tvs),
                "other_power": safe_float(other_power),
                "brand": brand,
                "price_limit": safe_float(price_limit) if price_limit else 22000,
                "inverter": safe_bool(inverter),
                "wifi": safe_bool(wifi),
                "mount_type": mount_type
            }
            
            order_params = {
                "visit_date": visit_date,
                "room_area": safe_float(room_area),
                "room_type": room_type,
                "discount": safe_int(discount),
                "installation_price": safe_float(installation_price)
            }
            
            new_aircon_order = {
                "order_params": order_params,
                "aircon_params": aircon_params
            }
            
            payload = {
                "id": order_id,
                "new_aircon_order": new_aircon_order
            }
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BACKEND_URL}/api/add_aircon_to_compose_order/", json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("success"):
                    msg = f"Кондиционер #{data.get('aircon_count', 0)} успешно добавлен к заказу!"
                    
                    # Получаем дефолтные значения для очистки полей
                    placeholder = get_placeholder_order()
                    
                    # Возвращаем сообщение, ID заказа и обновленные значения полей (очищенные)
                    return (
                        msg, 
                        order_id,
                        # Данные клиента остаются без изменений (включая visit_date и discount)
                        client_name, client_phone, client_mail, client_address, visit_date, discount,
                        # Поля помещения очищаются к дефолтным значениям (возвращаем правильные типы для Gradio)
                        50.0,  # compose_area (float для слайдера)
                        "",    # compose_type_room (строка для текстбокса)
                        False, # compose_wifi (bool для чекбокса)
                        False, # compose_inverter (bool для чекбокса)
                        10000.0, # compose_price (float для слайдера)
                        "Любой", # compose_mount_type (строка для дропдауна)
                        2.7,   # compose_ceiling_height (float для слайдера)
                        "Средняя", # compose_illumination (строка для дропдауна)
                        1,     # compose_num_people (int для слайдера)
                        "Сидячая работа", # compose_activity (строка для дропдауна)
                        0,     # compose_num_computers (int для слайдера)
                        0,     # compose_num_tvs (int для слайдера)
                        0.0,   # compose_other_power (float для слайдера)
                        "Любой", # compose_brand (строка для дропдауна)
                        666.0  # compose_installation_price (float для number поля)
                    )
                else:
                    error_msg = data.get("error", "Неизвестная ошибка от бэкенда.")
                    return f"Ошибка: {error_msg}", order_id, client_name, client_phone, client_mail, client_address, visit_date, discount, 50.0, "", False, False, 10000.0, "Любой", 2.7, "Средняя", 1, "Сидячая работа", 0, 0, 0.0, "Любой", 666.0
                    
        except Exception as e:
            logger.error(f"Ошибка при добавлении кондиционера: {e}", exc_info=True)
            return f"Ошибка: {e}", order_id, client_name, client_phone, client_mail, client_address, visit_date, discount, 50.0, "", False, False, 10000.0, "Любой", 2.7, "Средняя", 1, "Сидячая работа", 0, 0, 0.0, "Любой", 666.0

    # Обработчик для удаления заказа
    async def delete_order_handler(order_id_hidden_value):
        """Обработчик удаления заказа"""
        logger.info(f"[DEBUG] delete_order_handler: order_id_hidden_value={order_id_hidden_value}")
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID заказа!", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), None, get_placeholder_order()
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return "Ошибка: Некорректный ID заказа!", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), None, get_placeholder_order()
        
        try:
            result = await delete_order(order_id)
            if result.get("success"):
                logger.info(f"Заказ {order_id} успешно удален")
                # Возвращаемся на корневую страницу и сбрасываем состояние
                return "Заказ успешно удален! Перенаправление на главную страницу...", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), None, get_placeholder_order()
            else:
                error_msg = result.get("error", "Неизвестная ошибка при удалении заказа")
                logger.error(f"Ошибка удаления заказа {order_id}: {error_msg}")
                return f"Ошибка: {error_msg}", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), order_id, None
        except Exception as e:
            logger.error(f"Ошибка при удалении заказа: {e}", exc_info=True)
            return f"Ошибка: {e}", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), order_id, None

    delete_btn.click(
        fn=delete_order_handler,
        inputs=[order_id_hidden],
        outputs=[aircons_output, start_screen, orders_list_screen, main_order_screen, order_id_hidden, order_state]
    )

    # Обработчик генерации КП для составного заказа
    async def generate_compose_kp_handler(order_id_hidden_value):
        """Обработчик генерации КП для составного заказа"""
        logger.info(f"[DEBUG] generate_compose_kp_handler: order_id_hidden_value={order_id_hidden_value}")
        
        try:
            order_id = int(order_id_hidden_value)
            if not order_id or order_id <= 0:
                return "Ошибка: Некорректный ID составного заказа!", None
        except Exception as e:
            logger.error(f"Ошибка преобразования order_id_hidden_value: {e}")
            return f"Ошибка: Некорректный ID составного заказа!", None
        
        try:
            # Отправляем только id заказа, бэкенд сам достанет все данные
            payload = {"id": order_id}
            logger.info(f"[DEBUG] generate_compose_kp_handler: payload: {json.dumps(payload, ensure_ascii=False)}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{BACKEND_URL}/api/generate_compose_offer/", json=payload)
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    logger.error(f"Ошибка от бэкенда: {data['error']}")
                    error_msg = data['error']
                    if "Нет кондиционеров с подобранными вариантами" in error_msg:
                        return f"Ошибка: {error_msg}\n\nДля генерации КП необходимо:\n1. Подобрать кондиционеры для каждого помещения (нажать кнопку 'Подобрать')\n2. Добавить все необходимые помещения (нажать кнопку 'Ввести данные для следующего кондиционера')\n3. Повторить подбор для каждого нового помещения", None
                    else:
                        return f"Ошибка: {error_msg}", None
                
                pdf_path = data.get("pdf_path", None)
                if pdf_path:
                    formatted_list = "Коммерческое предложение для составного заказа успешно сгенерировано! Пожалуйста, скачайте PDF файл."
                    logger.info(f"КП для составного заказа {order_id} успешно сформировано.")
                    return formatted_list, pdf_path
                else:
                    return "Ошибка: PDF файл не был создан", None
                    
        except httpx.RequestError as e:
            error_message = f"Не удалось связаться с бэкендом: {e}"
            logger.error(error_message, exc_info=True)
            return error_message, None
        except Exception as e:
            error_message = f"Произошла внутренняя ошибка: {e}"
            logger.error(error_message, exc_info=True)
            return error_message, None

    # --- Привязка обработчиков для составного заказа ---
    compose_save_btn.click(
        fn=save_compose_order_handler,
        inputs=[compose_order_id_hidden, compose_name, compose_phone, compose_mail, compose_address, compose_date, 
               compose_area, compose_type_room, compose_discount, compose_wifi, compose_inverter, compose_price, 
               compose_mount_type, compose_ceiling_height, compose_illumination, compose_num_people, compose_activity, 
               compose_num_computers, compose_num_tvs, compose_other_power, compose_brand, compose_installation_price],
        outputs=[compose_save_status, compose_order_id_hidden]
    )
    
    compose_select_btn.click(
        fn=select_compose_aircons_handler,
        inputs=[compose_order_id_hidden],
        outputs=[compose_aircons_output]
    )
    
    compose_add_aircon_btn.click(
        fn=add_next_aircon_handler,
        inputs=[compose_order_id_hidden, compose_name, compose_phone, compose_mail, compose_address, compose_date, 
               compose_area, compose_type_room, compose_discount, compose_wifi, compose_inverter, compose_price, 
               compose_mount_type, compose_ceiling_height, compose_illumination, compose_num_people, compose_activity, 
               compose_num_computers, compose_num_tvs, compose_other_power, compose_brand, compose_installation_price],
        outputs=[compose_save_status, compose_order_id_hidden, compose_name, compose_phone, compose_mail, compose_address, compose_date,
                compose_area, compose_type_room, compose_discount, compose_wifi, compose_inverter, compose_price,
                compose_mount_type, compose_ceiling_height, compose_illumination, compose_num_people, compose_activity,
                compose_num_computers, compose_num_tvs, compose_other_power, compose_brand, compose_installation_price]
    )
    
    compose_generate_kp_btn.click(
        fn=generate_compose_kp_handler,
        inputs=[compose_order_id_hidden],
        outputs=[compose_kp_status, compose_pdf_output]
    )