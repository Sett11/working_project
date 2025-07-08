import gradio as gr
import requests  # Импортируем requests для HTTP-запросов
import json
from utils.mylogger import Logger

# Инициализация логгера для фронтенда
logger = Logger("front", "logs/front.log")

# Адрес нашего FastAPI бэкенда
BACKEND_URL = "http://localhost:8000"


def generate_kp(name,
                phone,
                mail,
                address,
                date,
                area,
                type_room,
                discount,
                wifi,
                inverter,
                price, # Добавил price, так как он был в интерфейсе
                x1,
                x2,
                x3,
                brand):
    """
    Отправляет запрос на бэкенд для генерации КП и возвращает результат.
    """
    logger.info(f"Получен запрос на генерацию КП для клиента: {name}")
    
    # Формируем данные для отправки на бэкенд
    payload = {
        "client_data": {
            "name": name,
            "phone": phone,
            "mail": mail,
            "address": address,
            "date": date
        },
        "order_params": {
            "area": area,
            "type_room": type_room,
            "discount": discount
        },
        "aircon_params": {
            "wifi": wifi,
            "inverter": inverter,
            "price_limit": price,
            "brand": brand
        }
    }
    
    try:
        # Вместо прямого вызова делаем запрос к API
        # TODO: Реализовать этот эндпоинт на бэкенде
        # response = requests.post(f"{BACKEND_URL}/generate_commercial_offer/", json=payload)
        # response.raise_for_status()  # Проверка на ошибки HTTP
        
        # data = response.json()
        # aircons_list = data.get("aircons_list", "")
        # pdf_path = data.get("pdf_path", None)

        # ВРЕМЕННАЯ ЗАГЛУШКА, пока нет эндпоинта
        logger.warning("Используется временная заглушка! API эндпоинт не реализован.")
        aircons_list = "Тут будут кондиционеры (API не готово)"
        pdf_path = None # Нужно будет получать путь к файлу от бэкенда

        logger.info(f"КП для клиента {name} успешно сформировано (заглушка).")
        return aircons_list, pdf_path

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к бэкенду: {e}", exc_info=True)
        return f"Ошибка сервера: {e}", None
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при генерации КП: {e}", exc_info=True)
        return f"Внутренняя ошибка: {e}", None


with gr.Blocks(title="Автоматизация продаж кондиционеров", theme="ocean") as app:
    gr.Markdown("## Ввод параметров клиента")
    
    with gr.Tab("Основное"):
        name = gr.Textbox(label="Имя клиента")
        phone = gr.Textbox(label="Телефон")
        mail = gr.Textbox(label="Электронная почта")
        address = gr.Textbox(label="Адрес")
        date = gr.Textbox(label="Актуальная дата")
        type_room = gr.Dropdown(["квартира", "дом", "офис", "производство"], label="Тип помещения")
        area = gr.Slider(10, 200, label="Площадь помещения (м²)")
        discount = gr.Slider(1, 50, label="Индивидуальная скидка %")
    
    with gr.Tab("Кондиционер"):
        wifi = gr.Checkbox(label="Wi-Fi управление")
        inverter = gr.Checkbox(label="Инверторный компрессор")
        price = gr.Textbox(label="Верхний порог стоимости")
        x1 = gr.Textbox(label="Параметр Х1")
        x2 = gr.Textbox(label="Параметр Х2")
        x3 = gr.Textbox(label="Параметр Х3")
        brand = gr.Dropdown(["Любой", "Mitsubishi", "Ballu", "Toshiba"], label="Бренд")
    
    with gr.Tab("Результат"):
        aircons_output = gr.Textbox(label="Подходящие модели", interactive=False)
        pdf_output = gr.File(label="Скачать КП")
        generate_btn = gr.Button("Сформировать КП")
    
    # Логика обработки
    generate_btn.click(
        fn=generate_kp,
        inputs=[name,
                phone,
                mail,
                address,
                date,
                area,
                type_room,
                discount,
                wifi,
                inverter,
                price, # Добавил price
                x1,
                x2,
                x3,
                brand],
        outputs=[aircons_output,
                 pdf_output]
    )


if __name__ == "__main__":
    logger.info("Gradio интерфейс запускается")
    app.launch(server_port=7860, server_name="localhost",auth=("admin","123password"))