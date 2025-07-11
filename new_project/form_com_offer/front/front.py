"""
Модуль фронтенда Gradio для системы формирования коммерческих предложений по кондиционерам.

Содержит:
- Загрузку и отображение каталога комплектующих
- Визуальный интерфейс для ввода параметров клиента, заказа, комплектующих
- Вызовы к backend API для подбора кондиционеров и генерации КП
- Подробное логирование действий пользователя и ошибок
"""
import gradio as gr
import requests
from utils.mylogger import Logger
import json
import os
import functools

# Инициализация логгера для фронтенда
# log_file указывается без папки logs, чтобы использовать дефолтную директорию логов.
logger = Logger(name=__name__, log_file="frontend.log")

# Адрес нашего FastAPI бэкенда (имя сервиса из docker-compose)
# Теперь он указывает на контейнер бэкенда, а не на localhost
BACKEND_URL = "http://backend:8000"

# Путь к каталогу комплектующих
COMPONENTS_CATALOG_PATH = os.path.join(os.path.dirname(__file__), '../docs/components_catalog.json')
PLACEHOLDER_IMAGE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../docs/images_comp/placeholder.jpg'))

def load_components_catalog():
    """
    Загружает каталог комплектующих из JSON-файла.
    Returns:
        dict: Данные каталога комплектующих.
    """
    with open(COMPONENTS_CATALOG_PATH, encoding='utf-8') as f:
        data = json.load(f)
    return data

def get_vozduhovody_options():
    """
    Возвращает список опций для воздуховодов из каталога комплектующих.
    Returns:
        list: Список словарей с id, name, image_url для воздуховодов.
    """
    data = load_components_catalog()
    vozduhovody = [c for c in data['components'] if c['category'] == 'Воздуховоды']
    options = []
    for c in vozduhovody:
        options.append({
            'id': c['id'],
            'name': c['name'],
            'image_url': c.get('image_url') if c.get('has_image') else PLACEHOLDER_IMAGE
        })
    return options

def get_vozduhovod_image(name):
    """
    Получает путь к изображению воздуховода по его названию.
    Args:
        name (str): Название воздуховода.
    Returns:
        str: Путь к изображению.
    """
    options = get_vozduhovody_options()
    for c in options:
        if c['name'] == name:
            return c['image_url']
    return PLACEHOLDER_IMAGE

def get_component_image(component_name):
    """
    Получает путь к изображению компонента по его названию.
    Args:
        component_name (str): Название компонента.
    Returns:
        str: Абсолютный путь к изображению или placeholder.
    """
    try:
        catalog = load_components_catalog()
        for component in catalog['components']:
            if component['name'].lower() == component_name.lower():
                if component.get('has_image') and component.get('image_url'):
                    # Получаем абсолютный путь к изображению
                    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', component['image_url']))
                    return abs_path
                else:
                    return PLACEHOLDER_IMAGE
        return PLACEHOLDER_IMAGE
    except Exception as e:
        logger.error(f"Ошибка при получении изображения для {component_name}: {e}")
        return PLACEHOLDER_IMAGE

def vozduhovody_ui(selected_names, lengths):
    """
    Генерирует UI-блок для выбора воздуховодов с изображениями и вводом длины.
    Args:
        selected_names (list): Список выбранных названий воздуховодов.
        lengths (list): Список длин для выбранных воздуховодов.
    Returns:
        tuple: Gradio-элементы для UI.
    """
    options = get_vozduhovody_options()
    names = [c['name'] for c in options]
    with gr.Column():
        gr.Markdown('#### Воздуховоды:')
        new_selected = gr.Dropdown(names, value=selected_names, multiselect=True, label='Выберите воздуховоды')
        images = []
        length_inputs = []
        remove_buttons = []
        for i, name in enumerate(selected_names):
            with gr.Row():
                img = gr.Image(get_vozduhovod_image(name), shape=(100,100), label=name)
                images.append(img)
                length = gr.Number(value=lengths[i] if i < len(lengths) else 1, label='Длина (м)', precision=0, minimum=1)
                length_inputs.append(length)
                remove_btn = gr.Button('Удалить', variant='stop')
                remove_buttons.append(remove_btn)
        add_btn = gr.Button('Добавить воздуховод', variant='primary')
    return new_selected, images, length_inputs, remove_buttons, add_btn

def generate_kp(name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, 
                ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand,
                # Параметры комплектующих
                airduct_500x800, airduct_500x800_qty, airduct_500x800_length,
                airduct_600x300, airduct_600x300_qty, airduct_600x300_length,
                airduct_800x500, airduct_800x500_qty, airduct_800x500_length,
                airduct_d450, airduct_d450_qty, airduct_d450_length,
                airduct_d560, airduct_d560_qty, airduct_d560_length,
                airduct_d630, airduct_d630_qty, airduct_d630_length,
                airduct_d710, airduct_d710_qty, airduct_d710_length,
                # Отводы
                bend_90_500x800, bend_90_500x800_qty,
                bend_90_d630, bend_90_d630_qty,
                bend_90_d560, bend_90_d560_qty,
                bend_90_d450, bend_90_d450_qty,
                bend_90_d710, bend_90_d710_qty,
                # Переходы
                transition_500x800_d630, transition_500x800_d630_qty,
                transition_600x300_d560, transition_600x300_d560_qty,
                transition_500x800_d450, transition_500x800_d450_qty,
                # Тройники
                tee_500x800, tee_500x800_qty,
                # Клапаны
                valve_800x500, valve_800x500_qty,
                valve_600x300, valve_600x300_qty,
                valve_d450, valve_d450_qty,
                # Соединительные элементы
                nipple, nipple_qty,
                coupling, coupling_qty,
                cap, cap_qty,
                # Регулирующие элементы
                damper, damper_qty,
                umbrella, umbrella_qty,
                deflector, deflector_qty,
                # Материалы
                steel_sheet, steel_sheet_qty, steel_sheet_length,
                insulation, insulation_qty, insulation_length):
    """
    Отправляет запрос на бэкенд для генерации КП и возвращает результат.
    Все параметры подробно описаны в сигнатуре функции.
    Returns:
        tuple: (строка с результатом подбора, путь к PDF или None)
    """
    logger.info(f"Получен запрос на генерацию КП для клиента: {name}")
    
    # Преобразуем значения для расчета мощности
    illumination_map = {"Слабая": 0, "Средняя": 1, "Сильная": 2}
    activity_map = {"Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
    
    # Собираем выбранные комплектующие
    selected_components = []
    
    # Воздуховоды
    if airduct_500x800:
        qty = airduct_500x800_qty or 0
        length = airduct_500x800_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Воздуховод 500x800", "qty": qty, "length": length})
    
    if airduct_600x300:
        qty = airduct_600x300_qty or 0
        length = airduct_600x300_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Воздуховод 600x300", "qty": qty, "length": length})
    
    if airduct_800x500:
        qty = airduct_800x500_qty or 0
        length = airduct_800x500_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Воздуховод 800x500", "qty": qty, "length": length})
    
    if airduct_d450:
        qty = airduct_d450_qty or 0
        length = airduct_d450_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Воздуховод ø450", "qty": qty, "length": length})
    
    if airduct_d560:
        qty = airduct_d560_qty or 0
        length = airduct_d560_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Воздуховод ø560", "qty": qty, "length": length})
    
    if airduct_d630:
        qty = airduct_d630_qty or 0
        length = airduct_d630_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Воздуховод ø630", "qty": qty, "length": length})
    
    if airduct_d710:
        qty = airduct_d710_qty or 0
        length = airduct_d710_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Воздуховод ø710", "qty": qty, "length": length})
    
    # Отводы
    if bend_90_500x800:
        qty = bend_90_500x800_qty or 0
        if qty > 0:
            selected_components.append({"name": "Поворот 90° 500x800", "qty": qty})
    
    if bend_90_d630:
        qty = bend_90_d630_qty or 0
        if qty > 0:
            selected_components.append({"name": "Поворот 90° ø630", "qty": qty})
    
    if bend_90_d560:
        qty = bend_90_d560_qty or 0
        if qty > 0:
            selected_components.append({"name": "Поворот 90° ø560", "qty": qty})
    
    if bend_90_d450:
        qty = bend_90_d450_qty or 0
        if qty > 0:
            selected_components.append({"name": "Поворот 90° ø450", "qty": qty})
    
    if bend_90_d710:
        qty = bend_90_d710_qty or 0
        if qty > 0:
            selected_components.append({"name": "Поворот 90° ø710", "qty": qty})
    
    # Переходы
    if transition_500x800_d630:
        qty = transition_500x800_d630_qty or 0
        if qty > 0:
            selected_components.append({"name": "Переход 500x800→ø630", "qty": qty})
    
    if transition_600x300_d560:
        qty = transition_600x300_d560_qty or 0
        if qty > 0:
            selected_components.append({"name": "Переход 600x300→ø560", "qty": qty})
    
    if transition_500x800_d450:
        qty = transition_500x800_d450_qty or 0
        if qty > 0:
            selected_components.append({"name": "Переход 500x800→ø450", "qty": qty})
    
    # Тройники
    if tee_500x800:
        qty = tee_500x800_qty or 0
        if qty > 0:
            selected_components.append({"name": "Тройник 500x800", "qty": qty})
    
    # Клапаны
    if valve_800x500:
        qty = valve_800x500_qty or 0
        if qty > 0:
            selected_components.append({"name": "Клапан РЕГУЛЯР-Л-800х500", "qty": qty})
    
    if valve_600x300:
        qty = valve_600x300_qty or 0
        if qty > 0:
            selected_components.append({"name": "Клапан РЕГУЛЯР-600*300", "qty": qty})
    
    if valve_d450:
        qty = valve_d450_qty or 0
        if qty > 0:
            selected_components.append({"name": "Клапан РЕГУЛЯР-Л-450", "qty": qty})
    
    # Соединительные элементы
    if nipple:
        qty = nipple_qty or 0
        if qty > 0:
            selected_components.append({"name": "Ниппель", "qty": qty})
    
    if coupling:
        qty = coupling_qty or 0
        if qty > 0:
            selected_components.append({"name": "Муфта", "qty": qty})
    
    if cap:
        qty = cap_qty or 0
        if qty > 0:
            selected_components.append({"name": "Заглушка", "qty": qty})
    
    # Регулирующие элементы
    if damper:
        qty = damper_qty or 0
        if qty > 0:
            selected_components.append({"name": "Дроссель-клапан", "qty": qty})
    
    if umbrella:
        qty = umbrella_qty or 0
        if qty > 0:
            selected_components.append({"name": "Зонт крышный", "qty": qty})
    
    if deflector:
        qty = deflector_qty or 0
        if qty > 0:
            selected_components.append({"name": "Дефлектор", "qty": qty})
    
    # Материалы
    if steel_sheet:
        qty = steel_sheet_qty or 0
        length = steel_sheet_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Сталь тонколистовая", "qty": qty, "length": length})
    
    if insulation:
        qty = insulation_qty or 0
        length = insulation_length or 0.0
        if qty > 0 or length > 0:
            selected_components.append({"name": "Маты минераловатные", "qty": qty, "length": length})
    
    payload = {
        "client_data": {"full_name": name, "phone": phone, "email": mail, "address": address},
        "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": date},
        "aircon_params": {
            "wifi": wifi, 
            "inverter": inverter, 
            "price_limit": price, 
            "brand": brand, 
            "mount_type": mount_type,
            # Параметры для расчета мощности
            "area": area,
            "ceiling_height": ceiling_height,
            "illumination": illumination_map.get(illumination, 1),
            "num_people": num_people,
            "activity": activity_map.get(activity, 0),
            "num_computers": num_computers,
            "num_tvs": num_tvs,
            "other_power": other_power
        },
        "components": selected_components
    }
    
    try:
        logger.info(f"Отправка запроса на эндпоинт /api/generate_offer/ на бэкенде.")
        response = requests.post(f"{BACKEND_URL}/api/generate_offer/", json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Проверяем на ошибки
        if "error" in data:
            logger.error(f"Ошибка от бэкенда: {data['error']}")
            return f"Ошибка: {data['error']}", None
        
        aircons_list = data.get("aircons_list", [])
        pdf_path = data.get("pdf_path", None)
        
        # Форматируем список кондиционеров для отображения
        if isinstance(aircons_list, list) and aircons_list:
            formatted_list = f"Найдено {data.get('total_count', len(aircons_list))} подходящих кондиционеров:\n\n"
            for i, aircon in enumerate(aircons_list, 1):
                formatted_list += f"{i}. {aircon.get('brand', 'N/A')} {aircon.get('model_name', 'N/A')}\n"
                formatted_list += f"   Мощность охлаждения: {aircon.get('cooling_power_kw', 'N/A')} кВт\n"
                formatted_list += f"   Мощность обогрева: {aircon.get('heating_power_kw', 'N/A')} кВт\n"
                formatted_list += f"   Цена: {aircon.get('retail_price_byn', 'N/A')} BYN\n"
                formatted_list += f"   Инвертор: {'Да' if aircon.get('is_inverter') else 'Нет'}\n"
                formatted_list += f"   Wi-Fi: {'Да' if aircon.get('has_wifi') else 'Нет'}\n"
                formatted_list += f"   Тип монтажа: {aircon.get('mount_type', 'N/A')}\n\n"
        else:
            formatted_list = "Подходящих кондиционеров не найдено."

        logger.info(f"КП для клиента {name} успешно сформировано.")
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
    """
    Подбирает только кондиционеры без генерации КП.
    Все параметры подробно описаны в сигнатуре функции.
    Returns:
        str: Список подходящих моделей или сообщение об ошибке.
    """
    logger.info(f"Подбор кондиционеров для клиента: {name}")
    
    # Преобразуем значения для расчета мощности
    illumination_map = {"Слабая": 0, "Средняя": 1, "Сильная": 2}
    activity_map = {"Сидячая работа": 0, "Легкая работа": 1, "Средняя работа": 2, "Тяжелая работа": 3, "Спорт": 4}
    
    payload = {
        "client_data": {"full_name": name, "phone": phone, "email": mail, "address": address},
        "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": date},
        "aircon_params": {
            "wifi": wifi, 
            "inverter": inverter, 
            "price_limit": price, 
            "brand": brand, 
            "mount_type": mount_type,
            # Параметры для расчета мощности
            "area": area,
            "ceiling_height": ceiling_height,
            "illumination": illumination_map.get(illumination, 1),
            "num_people": num_people,
            "activity": activity_map.get(activity, 0),
            "num_computers": num_computers,
            "num_tvs": num_tvs,
            "other_power": other_power
        }
    }
    
    try:
        logger.info(f"Отправка запроса на эндпоинт /api/select_aircons/ на бэкенде.")
        response = requests.post(f"{BACKEND_URL}/api/select_aircons/", json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Проверяем на ошибки
        if "error" in data:
            logger.error(f"Ошибка от бэкенда: {data['error']}")
            return f"Ошибка: {data['error']}"
        
        aircons_list = data.get("aircons_list", [])
        
        # Форматируем список кондиционеров для отображения
        if isinstance(aircons_list, list) and aircons_list:
            formatted_list = f"Найдено {data.get('total_count', len(aircons_list))} подходящих кондиционеров:\n\n"
            for i, aircon in enumerate(aircons_list, 1):
                formatted_list += f"{i}. {aircon.get('brand', 'N/A')} {aircon.get('model_name', 'N/A')}\n"
                formatted_list += f"   Мощность охлаждения: {aircon.get('cooling_power_kw', 'N/A')} кВт\n"
                formatted_list += f"   Мощность обогрева: {aircon.get('heating_power_kw', 'N/A')} кВт\n"
                formatted_list += f"   Цена: {aircon.get('retail_price_byn', 'N/A')} BYN\n"
                formatted_list += f"   Инвертор: {'Да' if aircon.get('is_inverter') else 'Нет'}\n"
                formatted_list += f"   Wi-Fi: {'Да' if aircon.get('has_wifi') else 'Нет'}\n"
                formatted_list += f"   Тип монтажа: {aircon.get('mount_type', 'N/A')}\n\n"
        else:
            formatted_list = "Подходящих кондиционеров не найдено."

        logger.info(f"Подбор кондиционеров для клиента {name} завершен успешно.")
        return formatted_list
        
    except requests.exceptions.RequestException as e:
        error_message = f"Не удалось связаться с бэкендом: {e}"
        logger.error(error_message, exc_info=True)
        return error_message
    except Exception as e:
        error_message = f"Произошла внутренняя ошибка: {e}"
        logger.error(error_message, exc_info=True)
        return error_message





# Функция create_component_card удалена, так как используется статический интерфейс

# Функция add_component_to_order удалена, так как используется упрощенная версия add_component_simple

# Определяем интерфейс Gradio
# Мы не запускаем его здесь, а просто создаем объект `app`
with gr.Blocks(title="Автоматизация продаж кондиционеров", theme=gr.themes.Soft()) as interface:
    gr.Markdown("# Система формирования коммерческих предложений")
    
    with gr.Tab("Данные для КП"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 1. Данные клиента")
                name = gr.Textbox(label="Имя клиента")
                phone = gr.Textbox(label="Телефон")
                mail = gr.Textbox(label="Электронная почта")
                address = gr.Textbox(label="Адрес")
                date = gr.Textbox(label="Дата визита монтажника")
            with gr.Column():
                gr.Markdown("### 2. Параметры заказа")
                type_room = gr.Dropdown(["квартира", "дом", "офис", "производство"], label="Тип помещения")
                area = gr.Slider(10, 200, value=50, label="Площадь помещения (м²)")
                discount = gr.Slider(0, 50, value=5, label="Индивидуальная скидка (%)")
        
        gr.Markdown("### 3. Требования к кондиционеру")
        with gr.Row():
            brand = gr.Dropdown(["Любой", "DANTEX", "VARIOUS"], label="Бренд")
            price = gr.Slider(1000, 10000, value=3000, label="Верхний порог стоимости (BYN)")
            inverter = gr.Checkbox(label="Инверторный компрессор")
            wifi = gr.Checkbox(label="Wi-Fi управление")
        with gr.Row():
            mount_type = gr.Dropdown(["Любой", "настенный", "кассетный", "потолочный", "напольный", "колонный"], 
                                   label="Тип монтажа", value="Любой")
        
        gr.Markdown("### 4. Дополнительные параметры для расчета мощности")
        with gr.Row():
            ceiling_height = gr.Slider(2.0, 5.0, value=2.7, step=0.1, label="Высота потолков (м)")
            illumination = gr.Dropdown(["Слабая", "Средняя", "Сильная"], value="Средняя", label="Освещенность")
            num_people = gr.Slider(1, 10, value=1, step=1, label="Количество людей")
            activity = gr.Dropdown(["Сидячая работа", "Легкая работа", "Средняя работа", "Тяжелая работа", "Спорт"], 
                                 value="Сидячая работа", label="Активность людей")
        with gr.Row():
            num_computers = gr.Slider(0, 10, value=0, step=1, label="Количество компьютеров")
            num_tvs = gr.Slider(0, 5, value=0, step=1, label="Количество телевизоров")
            other_power = gr.Slider(0, 2000, value=0, step=50, label="Мощность прочей техники (Вт)")

    with gr.Tab("Комплектующие"):
        gr.Markdown("### Подбор комплектующих для монтажа")
        
        # Блок 1: Воздуховоды
        with gr.Group():
            gr.Markdown("#### Воздуховоды")
            
            # Прямоугольные воздуховоды
            with gr.Row():
                airduct_500x800 = gr.Checkbox(label="500x800 мм")
                airduct_500x800_img = gr.Image(value=get_component_image("воздуховод 500х800"), label="Фото", height=80, width=80, interactive=False)
                airduct_500x800_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                airduct_500x800_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
            
            with gr.Row():
                airduct_600x300 = gr.Checkbox(label="600x300 мм")
                airduct_600x300_img = gr.Image(value=get_component_image("воздуховод 600х300"), label="Фото", height=80, width=80, interactive=False)
                airduct_600x300_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                airduct_600x300_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
            
            with gr.Row():
                airduct_800x500 = gr.Checkbox(label="800x500 мм")
                airduct_800x500_img = gr.Image(value=get_component_image("воздуховод 800х500"), label="Фото", height=80, width=80, interactive=False)
                airduct_800x500_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                airduct_800x500_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
            
            # Круглые воздуховоды
            with gr.Row():
                airduct_d450 = gr.Checkbox(label="ø450 мм")
                airduct_d450_img = gr.Image(value=get_component_image("воздуховод d450"), label="Фото", height=80, width=80, interactive=False)
                airduct_d450_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                airduct_d450_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
            
            with gr.Row():
                airduct_d560 = gr.Checkbox(label="ø560 мм")
                airduct_d560_img = gr.Image(value=get_component_image("воздуховод d560"), label="Фото", height=80, width=80, interactive=False)
                airduct_d560_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                airduct_d560_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
            
            with gr.Row():
                airduct_d630 = gr.Checkbox(label="ø630 мм")
                airduct_d630_img = gr.Image(value=get_component_image("воздуховод d630"), label="Фото", height=80, width=80, interactive=False)
                airduct_d630_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                airduct_d630_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
            
            with gr.Row():
                airduct_d710 = gr.Checkbox(label="ø710 мм")
                airduct_d710_img = gr.Image(value=get_component_image("воздуховод d710"), label="Фото", height=80, width=80, interactive=False)
                airduct_d710_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                airduct_d710_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
        
        # Блок 2: Отводы и повороты
        with gr.Group():
            gr.Markdown("#### Отводы и повороты")
            
            with gr.Row():
                bend_90_500x800 = gr.Checkbox(label="Поворот 90° 500x800 мм")
                bend_90_500x800_img = gr.Image(value=get_component_image("поворот 90° 500х800"), label="Фото", height=80, width=80, interactive=False)
                bend_90_500x800_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                bend_90_d630 = gr.Checkbox(label="Поворот 90° ø630 мм")
                bend_90_d630_img = gr.Image(value=get_component_image("поворот 90° d630"), label="Фото", height=80, width=80, interactive=False)
                bend_90_d630_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                bend_90_d560 = gr.Checkbox(label="Поворот 90° ø560 мм")
                bend_90_d560_img = gr.Image(value=get_component_image("поворот 90° d560"), label="Фото", height=80, width=80, interactive=False)
                bend_90_d560_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                bend_90_d450 = gr.Checkbox(label="Поворот 90° ø450 мм")
                bend_90_d450_img = gr.Image(value=get_component_image("поворот 90° d450"), label="Фото", height=80, width=80, interactive=False)
                bend_90_d450_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                bend_90_d710 = gr.Checkbox(label="Поворот 90° ø710 мм")
                bend_90_d710_img = gr.Image(value=get_component_image("поворот 90° d710"), label="Фото", height=80, width=80, interactive=False)
                bend_90_d710_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
        
        # Блок 3: Переходы
        with gr.Group():
            gr.Markdown("#### Переходы")
            
            with gr.Row():
                transition_500x800_d630 = gr.Checkbox(label="500x800 → ø630 мм")
                transition_500x800_d630_img = gr.Image(value=get_component_image("переход 500х800/d630"), label="Фото", height=80, width=80, interactive=False)
                transition_500x800_d630_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                transition_600x300_d560 = gr.Checkbox(label="600x300 → ø560 мм")
                transition_600x300_d560_img = gr.Image(value=get_component_image("переход 600х300/d560"), label="Фото", height=80, width=80, interactive=False)
                transition_600x300_d560_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                transition_500x800_d450 = gr.Checkbox(label="500x800 → ø450 мм")
                transition_500x800_d450_img = gr.Image(value=get_component_image("переход 500х800/d450"), label="Фото", height=80, width=80, interactive=False)
                transition_500x800_d450_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
        
        # Блок 4: Тройники
        with gr.Group():
            gr.Markdown("#### Тройники")
            
            with gr.Row():
                tee_500x800 = gr.Checkbox(label="500x800/800x500/500x800 мм")
                tee_500x800_img = gr.Image(value=get_component_image("тройник 500х800/800х500/500х800"), label="Фото", height=80, width=80, interactive=False)
                tee_500x800_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
        
        # Блок 5: Клапаны
        with gr.Group():
            gr.Markdown("#### Клапаны")
            
            with gr.Row():
                valve_800x500 = gr.Checkbox(label="РЕГУЛЯР-Л-800х500-В-1")
                valve_800x500_img = gr.Image(value=get_component_image("Клапан воздушный регулирующий РЕГУЛЯР-Л-800х500-В-1"), label="Фото", height=80, width=80, interactive=False)
                valve_800x500_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                valve_600x300 = gr.Checkbox(label="РЕГУЛЯР-600*300-Н-1")
                valve_600x300_img = gr.Image(value=get_component_image("Клапан воздушный регулирующий РЕГУЛЯР-600*300-Н-1"), label="Фото", height=80, width=80, interactive=False)
                valve_600x300_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                valve_d450 = gr.Checkbox(label="РЕГУЛЯР-Л-450-Н-1")
                valve_d450_img = gr.Image(value=get_component_image("Клапан воздушный регулирующий РЕГУЛЯР-Л-450-Н-1"), label="Фото", height=80, width=80, interactive=False)
                valve_d450_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
        
        # Блок 6: Соединительные элементы
        with gr.Group():
            gr.Markdown("#### Соединительные элементы")
            
            with gr.Row():
                nipple = gr.Checkbox(label="Ниппель ø100-1250 мм")
                nipple_img = gr.Image(value=get_component_image("ниппель"), label="Фото", height=80, width=80, interactive=False)
                nipple_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                coupling = gr.Checkbox(label="Муфта ø100-1250 мм")
                coupling_img = gr.Image(value=get_component_image("муфта"), label="Фото", height=80, width=80, interactive=False)
                coupling_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                cap = gr.Checkbox(label="Заглушка круглая ø100-1250 мм")
                cap_img = gr.Image(value=get_component_image("заглушка"), label="Фото", height=80, width=80, interactive=False)
                cap_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
        
        # Блок 7: Регулирующие элементы
        with gr.Group():
            gr.Markdown("#### Регулирующие элементы")
            
            with gr.Row():
                damper = gr.Checkbox(label="Дроссель-клапан ø100-500 мм")
                damper_img = gr.Image(value=get_component_image("дроссель-клапан"), label="Фото", height=80, width=80, interactive=False)
                damper_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                umbrella = gr.Checkbox(label="Зонт крышный ø100-710 мм")
                umbrella_img = gr.Image(value=get_component_image("зонт крышный"), label="Фото", height=80, width=80, interactive=False)
                umbrella_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
            
            with gr.Row():
                deflector = gr.Checkbox(label="Дефлектор ø200-1250 мм")
                deflector_img = gr.Image(value=get_component_image("дефлектор"), label="Фото", height=80, width=80, interactive=False)
                deflector_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
        
        # Блок 8: Материалы
        with gr.Group():
            gr.Markdown("#### Материалы")
            
            with gr.Row():
                steel_sheet = gr.Checkbox(label="Тонколистовая оц. сталь б=0,5мм")
                steel_sheet_img = gr.Image(value=get_component_image("сталь тонколистовая"), label="Фото", height=80, width=80, interactive=False)
                steel_sheet_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                steel_sheet_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
            
            with gr.Row():
                insulation = gr.Checkbox(label="Маты минераловатные Акотерм СТИ 50/А")
                insulation_img = gr.Image(value=get_component_image("маты минераловатные"), label="Фото", height=80, width=80, interactive=False)
                insulation_qty = gr.Number(label="Количество (шт)", minimum=0, step=1, value=0)
                insulation_length = gr.Number(label="Длина (м)", minimum=0, step=0.1, value=0.0)
        
        # Статус выбора компонентов
        components_status = gr.Textbox(label="Статус выбора", interactive=False, value="Выберите нужные комплектующие")
        
        def collect_selected_components(
            # Воздуховоды
            airduct_500x800, airduct_500x800_qty, airduct_500x800_length,
            airduct_600x300, airduct_600x300_qty, airduct_600x300_length,
            airduct_800x500, airduct_800x500_qty, airduct_800x500_length,
            airduct_d450, airduct_d450_qty, airduct_d450_length,
            airduct_d560, airduct_d560_qty, airduct_d560_length,
            airduct_d630, airduct_d630_qty, airduct_d630_length,
            airduct_d710, airduct_d710_qty, airduct_d710_length,
            # Отводы
            bend_90_500x800, bend_90_500x800_qty,
            bend_90_d630, bend_90_d630_qty,
            bend_90_d560, bend_90_d560_qty,
            bend_90_d450, bend_90_d450_qty,
            bend_90_d710, bend_90_d710_qty,
            # Переходы
            transition_500x800_d630, transition_500x800_d630_qty,
            transition_600x300_d560, transition_600x300_d560_qty,
            transition_500x800_d450, transition_500x800_d450_qty,
            # Тройники
            tee_500x800, tee_500x800_qty,
            # Клапаны
            valve_800x500, valve_800x500_qty,
            valve_600x300, valve_600x300_qty,
            valve_d450, valve_d450_qty,
            # Соединительные элементы
            nipple, nipple_qty,
            coupling, coupling_qty,
            cap, cap_qty,
            # Регулирующие элементы
            damper, damper_qty,
            umbrella, umbrella_qty,
            deflector, deflector_qty,
            # Материалы
            steel_sheet, steel_sheet_qty, steel_sheet_length,
            insulation, insulation_qty, insulation_length
        ):
            """Собирает выбранные компоненты."""
            selected = []
            
            # Воздуховоды
            if airduct_500x800:
                qty = airduct_500x800_qty or 0
                length = airduct_500x800_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Воздуховод 500x800: {qty} шт, {length} м")
            
            if airduct_600x300:
                qty = airduct_600x300_qty or 0
                length = airduct_600x300_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Воздуховод 600x300: {qty} шт, {length} м")
            
            if airduct_800x500:
                qty = airduct_800x500_qty or 0
                length = airduct_800x500_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Воздуховод 800x500: {qty} шт, {length} м")
            
            if airduct_d450:
                qty = airduct_d450_qty or 0
                length = airduct_d450_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Воздуховод ø450: {qty} шт, {length} м")
            
            if airduct_d560:
                qty = airduct_d560_qty or 0
                length = airduct_d560_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Воздуховод ø560: {qty} шт, {length} м")
            
            if airduct_d630:
                qty = airduct_d630_qty or 0
                length = airduct_d630_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Воздуховод ø630: {qty} шт, {length} м")
            
            if airduct_d710:
                qty = airduct_d710_qty or 0
                length = airduct_d710_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Воздуховод ø710: {qty} шт, {length} м")
            
            # Отводы
            if bend_90_500x800:
                qty = bend_90_500x800_qty or 0
                if qty > 0:
                    selected.append(f"Поворот 90° 500x800: {qty} шт")
            
            if bend_90_d630:
                qty = bend_90_d630_qty or 0
                if qty > 0:
                    selected.append(f"Поворот 90° ø630: {qty} шт")
            
            if bend_90_d560:
                qty = bend_90_d560_qty or 0
                if qty > 0:
                    selected.append(f"Поворот 90° ø560: {qty} шт")
            
            if bend_90_d450:
                qty = bend_90_d450_qty or 0
                if qty > 0:
                    selected.append(f"Поворот 90° ø450: {qty} шт")
            
            if bend_90_d710:
                qty = bend_90_d710_qty or 0
                if qty > 0:
                    selected.append(f"Поворот 90° ø710: {qty} шт")
            
            # Переходы
            if transition_500x800_d630:
                qty = transition_500x800_d630_qty or 0
                if qty > 0:
                    selected.append(f"Переход 500x800→ø630: {qty} шт")
            
            if transition_600x300_d560:
                qty = transition_600x300_d560_qty or 0
                if qty > 0:
                    selected.append(f"Переход 600x300→ø560: {qty} шт")
            
            if transition_500x800_d450:
                qty = transition_500x800_d450_qty or 0
                if qty > 0:
                    selected.append(f"Переход 500x800→ø450: {qty} шт")
            
            # Тройники
            if tee_500x800:
                qty = tee_500x800_qty or 0
                if qty > 0:
                    selected.append(f"Тройник 500x800: {qty} шт")
            
            # Клапаны
            if valve_800x500:
                qty = valve_800x500_qty or 0
                if qty > 0:
                    selected.append(f"Клапан РЕГУЛЯР-Л-800х500: {qty} шт")
            
            if valve_600x300:
                qty = valve_600x300_qty or 0
                if qty > 0:
                    selected.append(f"Клапан РЕГУЛЯР-600*300: {qty} шт")
            
            if valve_d450:
                qty = valve_d450_qty or 0
                if qty > 0:
                    selected.append(f"Клапан РЕГУЛЯР-Л-450: {qty} шт")
            
            # Соединительные элементы
            if nipple:
                qty = nipple_qty or 0
                if qty > 0:
                    selected.append(f"Ниппель: {qty} шт")
            
            if coupling:
                qty = coupling_qty or 0
                if qty > 0:
                    selected.append(f"Муфта: {qty} шт")
            
            if cap:
                qty = cap_qty or 0
                if qty > 0:
                    selected.append(f"Заглушка: {qty} шт")
            
            # Регулирующие элементы
            if damper:
                qty = damper_qty or 0
                if qty > 0:
                    selected.append(f"Дроссель-клапан: {qty} шт")
            
            if umbrella:
                qty = umbrella_qty or 0
                if qty > 0:
                    selected.append(f"Зонт крышный: {qty} шт")
            
            if deflector:
                qty = deflector_qty or 0
                if qty > 0:
                    selected.append(f"Дефлектор: {qty} шт")
            
            # Материалы
            if steel_sheet:
                qty = steel_sheet_qty or 0
                length = steel_sheet_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Сталь тонколистовая: {qty} шт, {length} м")
            
            if insulation:
                qty = insulation_qty or 0
                length = insulation_length or 0.0
                if qty > 0 or length > 0:
                    selected.append(f"Маты минераловатные: {qty} шт, {length} м")
            
            if selected:
                return f"Выбрано {len(selected)} позиций:\n" + "\n".join(selected)
            else:
                return "Не выбрано ни одной позиции"
        
        # Кнопка для сбора выбранных компонентов
        collect_btn = gr.Button("Собрать выбранные компоненты", variant="primary")
        collect_btn.click(
            fn=collect_selected_components,
            inputs=[
                # Воздуховоды
                airduct_500x800, airduct_500x800_qty, airduct_500x800_length,
                airduct_600x300, airduct_600x300_qty, airduct_600x300_length,
                airduct_800x500, airduct_800x500_qty, airduct_800x500_length,
                airduct_d450, airduct_d450_qty, airduct_d450_length,
                airduct_d560, airduct_d560_qty, airduct_d560_length,
                airduct_d630, airduct_d630_qty, airduct_d630_length,
                airduct_d710, airduct_d710_qty, airduct_d710_length,
                # Отводы
                bend_90_500x800, bend_90_500x800_qty,
                bend_90_d630, bend_90_d630_qty,
                bend_90_d560, bend_90_d560_qty,
                bend_90_d450, bend_90_d450_qty,
                bend_90_d710, bend_90_d710_qty,
                # Переходы
                transition_500x800_d630, transition_500x800_d630_qty,
                transition_600x300_d560, transition_600x300_d560_qty,
                transition_500x800_d450, transition_500x800_d450_qty,
                # Тройники
                tee_500x800, tee_500x800_qty,
                # Клапаны
                valve_800x500, valve_800x500_qty,
                valve_600x300, valve_600x300_qty,
                valve_d450, valve_d450_qty,
                # Соединительные элементы
                nipple, nipple_qty,
                coupling, coupling_qty,
                cap, cap_qty,
                # Регулирующие элементы
                damper, damper_qty,
                umbrella, umbrella_qty,
                deflector, deflector_qty,
                # Материалы
                steel_sheet, steel_sheet_qty, steel_sheet_length,
                insulation, insulation_qty, insulation_length
            ],
            outputs=[components_status]
        )
    
    with gr.Tab("Результат"):
        gr.Markdown("### Подбор кондиционеров")
        aircons_output = gr.Textbox(label="Подходящие модели", interactive=False, lines=15, max_lines=30)
        select_aircons_btn = gr.Button("Подобрать кондиционеры", variant="primary")
        
        gr.Markdown("### Генерация коммерческого предложения")
        pdf_output = gr.File(label="Скачать коммерческое предложение")
        generate_btn = gr.Button("Сформировать КП", variant="primary")
    
    # Обработчик для подбора кондиционеров
    select_aircons_btn.click(
        fn=select_aircons,
        inputs=[name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, 
                ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand],
        outputs=[aircons_output]
    )
    
    # Обработчик для генерации КП (включает и кондиционеры, и комплектующие)
    generate_btn.click(
        fn=generate_kp,
        inputs=[name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, 
                ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand,
                # Добавляем все параметры комплектующих
                airduct_500x800, airduct_500x800_qty, airduct_500x800_length,
                airduct_600x300, airduct_600x300_qty, airduct_600x300_length,
                airduct_800x500, airduct_800x500_qty, airduct_800x500_length,
                airduct_d450, airduct_d450_qty, airduct_d450_length,
                airduct_d560, airduct_d560_qty, airduct_d560_length,
                airduct_d630, airduct_d630_qty, airduct_d630_length,
                airduct_d710, airduct_d710_qty, airduct_d710_length,
                # Отводы
                bend_90_500x800, bend_90_500x800_qty,
                bend_90_d630, bend_90_d630_qty,
                bend_90_d560, bend_90_d560_qty,
                bend_90_d450, bend_90_d450_qty,
                bend_90_d710, bend_90_d710_qty,
                # Переходы
                transition_500x800_d630, transition_500x800_d630_qty,
                transition_600x300_d560, transition_600x300_d560_qty,
                transition_500x800_d450, transition_500x800_d450_qty,
                # Тройники
                tee_500x800, tee_500x800_qty,
                # Клапаны
                valve_800x500, valve_800x500_qty,
                valve_600x300, valve_600x300_qty,
                valve_d450, valve_d450_qty,
                # Соединительные элементы
                nipple, nipple_qty,
                coupling, coupling_qty,
                cap, cap_qty,
                # Регулирующие элементы
                damper, damper_qty,
                umbrella, umbrella_qty,
                deflector, deflector_qty,
                # Материалы
                steel_sheet, steel_sheet_qty, steel_sheet_length,
                insulation, insulation_qty, insulation_length],
        outputs=[aircons_output, pdf_output]
    )
