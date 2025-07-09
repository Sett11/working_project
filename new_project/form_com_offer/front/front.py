import gradio as gr
import requests
from utils.mylogger import Logger

# Инициализация логгера для фронтенда
logger = Logger(name=__name__, log_file="frontend.log")

# Адрес нашего FastAPI бэкенда (имя сервиса из docker-compose)
# Теперь он указывает на контейнер бэкенда, а не на localhost
BACKEND_URL = "http://backend:8000"

def generate_kp(name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, 
                ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand):
    """
    Отправляет запрос на бэкенд для генерации КП и возвращает результат.
    """
    logger.info(f"Получен запрос на генерацию КП для клиента: {name}")
    
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

def select_components(category, price_limit):
    """
    Подбирает комплектующие по заданным параметрам.
    """
    logger.info(f"Подбор комплектующих: категория={category}, цена до {price_limit} BYN")
    
    try:
        # Формируем параметры для запроса
        params = {
            "category": category if category != "Все категории" else None,
            "price_limit": price_limit
        }
        
        # Отправляем запрос на бэкенд
        response = requests.post(f"{BACKEND_URL}/api/select_components/", json=params)
        response.raise_for_status()
        data = response.json()
        
        # Проверяем на ошибки
        if "error" in data:
            logger.error(f"Ошибка от бэкенда: {data['error']}")
            return f"Ошибка: {data['error']}"
        
        components_list = data.get("components_list", [])
        
        # Форматируем список комплектующих для отображения
        if isinstance(components_list, list) and components_list:
            formatted_list = f"Найдено {data.get('total_count', len(components_list))} подходящих комплектующих:\n\n"
            for i, component in enumerate(components_list, 1):
                formatted_list += f"{i}. {component.get('name', 'N/A')}\n"
                formatted_list += f"   Категория: {component.get('category', 'N/A')}\n"
                formatted_list += f"   Размер: {component.get('size', 'N/A')}\n"
                formatted_list += f"   Материал: {component.get('material', 'N/A')}\n"
                formatted_list += f"   Цена: {component.get('price', 'N/A')} {component.get('currency', 'BYN')}\n"
                formatted_list += f"   Характеристики: {component.get('characteristics', 'N/A')}\n\n"
        else:
            formatted_list = "Подходящих комплектующих не найдено."

        logger.info(f"Подбор комплектующих завершен успешно.")
        return formatted_list
        
    except requests.exceptions.RequestException as e:
        error_message = f"Не удалось связаться с бэкендом: {e}"
        logger.error(error_message, exc_info=True)
        return error_message
    except Exception as e:
        error_message = f"Произошла внутренняя ошибка: {e}"
        logger.error(error_message, exc_info=True)
        return error_message

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
        with gr.Row():
            components_category = gr.Dropdown([
                "Все категории", "Воздуховоды", "Гибкие соединения", "Клапаны", 
                "Материалы", "Оборудование", "Отводы и повороты", "Переходы", 
                "Регулирующие элементы", "Соединительные элементы", "Тройники"
            ], label="Категория комплектующих", value="Все категории")
            components_price_limit = gr.Slider(100, 10000, value=2000, label="Максимальная цена (BYN)")
        
        with gr.Row():
            components_output = gr.Textbox(label="Подходящие комплектующие", interactive=False, lines=10, max_lines=20)
            select_components_btn = gr.Button("Подобрать комплектующие", variant="secondary")
    
    with gr.Tab("Результат"):
        aircons_output = gr.Textbox(label="Подходящие модели", interactive=False, lines=15, max_lines=30)
        pdf_output = gr.File(label="Скачать коммерческое предложение")
        generate_btn = gr.Button("Сформировать КП", variant="primary")
    
    generate_btn.click(
        fn=generate_kp,
        inputs=[name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, mount_type, 
                ceiling_height, illumination, num_people, activity, num_computers, num_tvs, other_power, brand],
        outputs=[aircons_output, pdf_output]
    )
    
    select_components_btn.click(
        fn=select_components,
        inputs=[components_category, components_price_limit],
        outputs=[components_output]
    )
