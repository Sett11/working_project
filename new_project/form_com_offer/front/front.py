"""
Модуль фронтенда Gradio для системы формирования коммерческих предложений по кондиционерам.
"""
import gradio as gr
import requests
from utils.mylogger import Logger
import json
import os
from collections import defaultdict

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

# ... (функции generate_kp и select_aircons остаются без изменений) ...
def generate_kp(client_name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type,
                ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand,
                installation_price, *components_inputs):
    logger.info(f"Получен запрос на генерацию КП для клиента: {client_name}")
    selected_components = []
    i = 0
    for component_data in COMPONENTS_CATALOG.get("components", []):
        is_selected = components_inputs[i]
        qty = components_inputs[i+1]
        length = components_inputs[i+2]
        i += 3
        if is_selected:
            comp_item = {"name": component_data["name"], "price": component_data.get("price", 0), "currency": COMPONENTS_CATALOG.get("catalog_info", {}).get("currency", "BYN"), "qty": int(qty) if qty else 0}
            if "труба" in comp_item["name"].lower() or "кабель" in comp_item["name"].lower() or "теплоизоляция" in comp_item["name"].lower() or "шланг" in comp_item["name"].lower():
                comp_item["unit"] = "м."
                comp_item["length"] = float(length) if length else 0.0
            else:
                comp_item["unit"] = "шт."
            if comp_item["qty"] > 0 or comp_item.get("length", 0) > 0:
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
        response = requests.post(f"{BACKEND_URL}/api/generate_offer/", json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            logger.error(f"Ошибка от бэкенда: {data['error']}")
            return f"Ошибка: {data['error']}", None
        pdf_path = data.get("pdf_path", None)
        formatted_list = "Коммерческое предложение генерируется... Пожалуйста, скачайте PDF файл."
        logger.info(f"КП для клиента {client_name} успешно сформировано.")
        return formatted_list, pdf_path
    except requests.exceptions.RequestException as e:
        error_message = f"Не удалось связаться с бэкендом: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, None
    except Exception as e:
        error_message = f"Произошла внутренняя ошибка: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, None

def select_aircons(name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type,
                   ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand):
    logger.info(f"Подбор кондиционеров для клиента: {name}")
    illumination_map = {"Слабая": 0, "Средняя": 1, "Сильная": 2}
    activity_map = {"Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
    payload = {"client_data": {"full_name": name, "phone": phone, "email": mail, "address": address}, "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": date}, "aircon_params": {"wifi": wifi, "inverter": inverter, "price_limit": price, "brand": brand, "mount_type": mount_type, "area": area, "ceiling_height": ceiling_height, "illumination": illumination_map.get(illumination, 1), "num_people": num_people, "activity": activity_map.get(activity, 0), "num_computers": num_computers, "num_tvs": num_tvs, "other_power": other_power}}
    try:
        logger.info(f"Отправка запроса на эндпоинт /api/select_aircons/ на бэкенде.")
        response = requests.post(f"{BACKEND_URL}/api/select_aircons/", json=payload)
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
    except requests.exceptions.RequestException as e:
        return f"Не удалось связаться с бэкендом: {e}"
    except Exception as e:
        return f"Произошла внутренняя ошибка: {e}"


# --- ГЛАВНЫЙ БЛОК ИНТЕРФЕЙСА С ИЗМЕНЕНИЯМИ ---
with gr.Blocks(title="Автоматизация продаж кондиционеров", theme=gr.themes.Ocean()) as interface:
    gr.Markdown("<h1 style='color:#00008B;'>Everis</h1>")
    gr.Markdown("<h2 style='color:#FAEBD7;'>Cистема формирования коммерческих предложений</h2>")

    # Вкладка "Данные для КП" без изменений
    with gr.Tab("Данные для КП"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 1. Данные клиента")
                name = gr.Textbox(label="Имя клиента", value="Иванов Иван")
                phone = gr.Textbox(label="Телефон", value="+375291234567")
                mail = gr.Textbox(label="Электронная почта", value="ivan@example.com")
                address = gr.Textbox(label="Адрес", value="г. Минск, ул. Ленина, 1")
                date = gr.Textbox(label="Дата визита монтажника", value="2025-07-12")
            with gr.Column():
                gr.Markdown("### 2. Параметры заказа")
                type_room = gr.Dropdown(["квартира", "дом", "офис", "производство"], label="Тип помещения")
                area = gr.Slider(10, 200, value=50, label="Площадь помещения (м²)")
                discount = gr.Slider(0, 50, value=5, label="Индивидуальная скидка (%)")
                installation_price = gr.Number(label="Стоимость монтажа (BYN)", minimum=0, step=1, value=0)
        gr.Markdown("### 3. Требования к кондиционеру")
        with gr.Row():
            brand = gr.Dropdown(["Любой", "LESSAR", "DANTEX", "AUX", "QuattroClima", "Tosot", "NiceME"], label="Бренд")
            price = gr.Slider(0, 10000, value=3000, label="Верхний порог стоимости (BYN)")
            inverter = gr.Checkbox(label="Инверторный компрессор")
            wifi = gr.Checkbox(label="Wi-Fi управление")
        with gr.Row():
            mount_type = gr.Dropdown(["Любой", "настенный", "кассетный", "потолочный", "напольный", "колонный"], label="Тип монтажа", value="Любой")
        gr.Markdown("### 4. Дополнительные параметры для расчета мощности")
        with gr.Row():
            ceiling_height = gr.Slider(2.0, 5.0, value=2.7, step=0.1, label="Высота потолков (м)")
            illumination = gr.Dropdown(["Слабая", "Средняя", "Сильная"], value="Средняя", label="Освещенность")
            num_people = gr.Slider(1, 10, value=1, step=1, label="Количество людей")
            activity = gr.Dropdown(["Сидячая работа", "Легкая работа", "Средняя работа", "Тяжелая работа", "Спорт"], value="Сидячая работа", label="Активность людей")
        with gr.Row():
            num_computers = gr.Slider(0, 10, value=0, step=1, label="Количество компьютеров")
            num_tvs = gr.Slider(0, 5, value=0, step=1, label="Количество телевизоров")
            other_power = gr.Slider(0, 2000, value=0, step=50, label="Мощность прочей техники (Вт)")

    # Вкладка "Комплектующие" с добавлением картинок
    with gr.Tab("Комплектующие"):
        gr.Markdown("### Подбор комплектующих для монтажа")
        components_ui_inputs = []
        components_by_category = defaultdict(list)
        for comp in COMPONENTS_CATALOG.get("components", []):
            components_by_category[comp["category"]].append(comp)
        
        for category, components_in_cat in components_by_category.items():
            with gr.Group():
                gr.Markdown(f"#### {category}")
                for comp in components_in_cat:
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=1):
                            image_path = get_component_image_path(comp.get('image_path'))
                            gr.Image(value=image_path, label="Фото", height=80, width=80, interactive=False)
                        
                        with gr.Column(scale=5):
                            is_measurable = "труба" in comp["name"].lower() or "кабель" in comp["name"].lower() or "теплоизоляция" in comp["name"].lower() or "шланг" in comp["name"].lower() or "провод" in comp["name"].lower()
                            label_text = f"{comp['name']}"
                            checkbox = gr.Checkbox(label=label_text)
                        
                        with gr.Column(scale=2):
                            qty_input = gr.Number(label="Кол-во (шт)", minimum=0, step=1, value=1)
                        
                        with gr.Column(scale=2):
                            if is_measurable:
                                length_input = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.1)
                            else:
                                length_input = gr.Number(visible=False)

                        components_ui_inputs.extend([checkbox, qty_input, length_input])

    # Вкладка "Результат" и обработчики без изменений
    with gr.Tab("Результат"):
        gr.Markdown("### Подбор кондиционеров")
        aircons_output = gr.TextArea(label="Подходящие модели", interactive=False, lines=15, max_lines=None, show_copy_button=True)
        select_aircons_btn = gr.Button("Подобрать кондиционеры", variant="primary")
        gr.Markdown("### Генерация коммерческого предложения")
        pdf_output = gr.File(label="Скачать коммерческое предложение")
        generate_btn = gr.Button("Сформировать КП", variant="primary")
    
    all_client_params = [name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand]
    select_aircons_btn.click(fn=select_aircons, inputs=all_client_params, outputs=[aircons_output])
    generate_btn.click(fn=generate_kp, inputs=all_client_params + [installation_price] + components_ui_inputs, outputs=[aircons_output, pdf_output])