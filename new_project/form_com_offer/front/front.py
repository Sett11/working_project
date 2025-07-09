import gradio as gr
import requests
from utils.mylogger import Logger

# Инициализация логгера для фронтенда
logger = Logger(name=__name__, log_file="frontend.log")

# Адрес нашего FastAPI бэкенда (имя сервиса из docker-compose)
# Теперь он указывает на контейнер бэкенда, а не на localhost
BACKEND_URL = "http://backend:8000"

def generate_kp(name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, x1, x2, x3, brand):
    """
    Отправляет запрос на бэкенд для генерации КП и возвращает результат.
    """
    logger.info(f"Получен запрос на генерацию КП для клиента: {name}")
    
    payload = {
        "client_data": {"full_name": name, "phone": phone, "email": mail, "address": address},
        "order_params": {"room_area": area, "room_type": type_room, "discount": discount, "visit_date": date},
        "aircon_params": {"wifi": wifi, "inverter": inverter, "price_limit": price, "brand": brand}
    }
    
    try:
        logger.info(f"Отправка запроса на эндпоинт /api/generate_offer/ на бэкенде.")
        # TODO: Реализовать этот эндпоинт на бэкенде
        # response = requests.post(f"{BACKEND_URL}/api/generate_offer/", json=payload)
        # response.raise_for_status()
        # data = response.json()
        # aircons_list = data.get("aircons_list", "")
        # pdf_path = data.get("pdf_path", None)

        # ВРЕМЕННАЯ ЗАГЛУШКА
        logger.warning("Используется временная заглушка! API эндпоинт /api/generate_offer/ не реализован.")
        aircons_list = "Здесь будет список подходящих кондиционеров (API эндпоинт не готов)."
        pdf_path = None

        logger.info(f"КП для клиента {name} успешно сформировано (использована заглушка).")
        return aircons_list, pdf_path

    except requests.exceptions.RequestException as e:
        error_message = f"Не удалось связаться с бэкендом: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, None
    except Exception as e:
        error_message = f"Произошла внутренняя ошибка: {e}"
        logger.error(error_message, exc_info=True)
        return error_message, None

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
            brand = gr.Dropdown(["Любой", "Mitsubishi", "Ballu", "Toshiba"], label="Бренд")
            price = gr.Slider(1000, 10000, value=3000, label="Верхний порог стоимости (BYN)")
            inverter = gr.Checkbox(label="Инверторный компрессор")
            wifi = gr.Checkbox(label="Wi-Fi управление")
        with gr.Row():
            x1 = gr.Textbox(label="Доп. параметр 1 (не используется)")
            x2 = gr.Textbox(label="Доп. параметр 2 (не используется)")
            x3 = gr.Textbox(label="Доп. параметр 3 (не используется)")

    with gr.Tab("Результат"):
        aircons_output = gr.Textbox(label="Подходящие модели", interactive=False)
        pdf_output = gr.File(label="Скачать коммерческое предложение")
        generate_btn = gr.Button("Сформировать КП", variant="primary")
    
    generate_btn.click(
        fn=generate_kp,
        inputs=[name, phone, mail, address, date, area, type_room, discount, wifi, inverter, price, x1, x2, x3, brand],
        outputs=[aircons_output, pdf_output]
    )
