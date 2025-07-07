import gradio as gr
from selection.aircon_selector import get_filtered_aircons
from selection.materials_calculator import get_complectations_for_cond
from utils.pdf_generator import create_kp_pdf
from utils.mylogger import Logger
from db.crud import save_client_data

logger = Logger("app", "logs")


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
                x1,
                x2,
                x3,
                brand):
    """Основная функция: сбор данных, подбор кондиционеров, генерация КП."""
    # Сохраняем данные клиента в БД
    client_id = save_client_data(name, phone, mail, address, date, area, type_room, discount)
    
    # Подбираем кондиционеры по параметрам
    aircons = get_filtered_aircons(area, type_room, wifi, inverter, x1, x2, x3, brand)
    aircons_list = "\n".join([f"{item['model']} ({item['price']} руб.)" for item in aircons])
    
    # Генерация PDF
    pdf_path = create_kp_pdf(client_id, aircons)
    logger.info("КП сгенерировано")
    return aircons_list, pdf_path


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
        price = gr.Textbox(label="Верхний п��рог стоимости")
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
                x1,
                x2,
                x3,
                brand],
        outputs=[aircons_output,
                 pdf_output]
    )


if __name__ == "__main__":
    logger.info("Приложение запущено")
    app.launch(server_port=7860, server_name="localhost",auth=("admin","123password"))