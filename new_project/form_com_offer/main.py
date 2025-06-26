import gradio as gr
# from select.aircon_selector import get_filtered_aircons
# from utils.pdf_generator import create_kp_pdf
# from db.crud import save_client_data

# Пример функции бизнес-логики (заглушка)
# def mock_get_filtered_aircons(area, wifi, inverter):
#     """Заглушка для теста интерфейса. Позже заменим на реальную функцию."""
#     return [
#         {"model": "Mitsubishi MSZ-LN25", "price": 899, "wifi": True, "inverter": True},
#         {"model": "Ballu BSEI-12HN1", "price": 499, "wifi": False, "inverter": False},
#     ]

# def generate_kp(name, phone, area, wifi, inverter, brand, notes):
#     """Основная функция: сбор данных, подбор кондиционеров, генерация КП."""
#     # 1. Сохраняем данные клиента в БД (пример)
#     client_id = save_client_data(name, phone, area, notes)
    
#     # 2. Подбираем кондиционеры по параметрам (заглушка)
#     aircons = mock_get_filtered_aircons(area, wifi, inverter)
#     aircons_list = "\n".join([f"{item['model']} ({item['price']} руб.)" for item in aircons])
    
    # 3. Генерация PDF (заглушка)
    # pdf_path = create_kp_pdf(client_id, aircons)
    
    # return aircons_list, pdf_path

# 3. Интерфейс Gradio
with gr.Blocks(title="Автоматизация продаж кондиционеров") as app:
    gr.Markdown("## Ввод параметров клиента")
    
    with gr.Tab("Основное"):
        name = gr.Textbox(label="Имя клиента")
        phone = gr.Textbox(label="Телефон")
        area = gr.Slider(10, 100, label="Площадь помещения (м²)")
        notes = gr.Textbox(label="Примечания", lines=3)
    
    with gr.Tab("Кондиционер"):
        wifi = gr.Checkbox(label="Wi-Fi управление")
        inverter = gr.Checkbox(label="Инверторный компрессор")
        brand = gr.Dropdown(["Любой", "Mitsubishi", "Ballu", "Toshiba"], label="Бренд")
    
    with gr.Tab("Результат"):
        aircons_output = gr.Textbox(label="Подходящие модели", interactive=False)
        pdf_output = gr.File(label="Скачать КП")
        generate_btn = gr.Button("Сформировать КП")
    
    # Логика обработки
    generate_btn.click(
        # fn=generate_kp,
        inputs=[name, phone, area, wifi, inverter, brand, notes],
        outputs=[aircons_output, pdf_output]
    )


if __name__ == "__main__":
    app.launch(server_port=7860, server_name="localhost")