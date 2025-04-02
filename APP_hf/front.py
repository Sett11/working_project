import gradio as gr
import aiohttp
import datetime
import asyncio
from logs import log_event as log_event_hf
from delete_files import delete_files

def log_event(message):
    log_event_hf(f"FROM FRONT: {message}")

def format_timestamp(timestamp):
    """
    returns a timestamp formatted as a string
    """
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

def get_timestamp():
    """
    returns the timestamp
    """
    return datetime.datetime.now().timestamp()

def update_slider():
    """
    updates the slider
    """
    return get_timestamp()

async def async_get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise):
    """
    processes the user"s request and returns a response
    """
    if file_bytes is None:
        log_event("Пользовательский файл не был загружен")
        return None, None
    log_event(f"Размер загружаемого файла: {len(file_bytes)} байт")
    # URL = "http://backend:8000/upload_file/" # для запуска в Docker
    URL = "http://localhost:8000/upload_file/" # для запуска на локальной машине
    data = aiohttp.FormData()  # Создаем объект FormData
    data.add_field("anonymize_names", str(anonymize_names))
    data.add_field("save_datetime", str(save_datetime))
    data.add_field("max_len_context", str(max_len_context))
    data.add_field("time_choise", format_timestamp(time_choise))
    data.add_field("file", file_bytes) # Добавляем файл в FormData
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, data=data) as response:
            out = await response.json()  # Получаем JSON-ответ
            if response.status == 200 and (r := out.get("result")):  # Проверяем статус ответа
                with open("result.txt", "w", encoding="utf8") as result_file:
                    result_file.write(r)
                code_name = out.get("code_name", {})  # получаем словарь code_name из ответа
                return "result.txt", "\n".join(f"{id}->{name}" for id, name in code_name.items()) if code_name else ""  # возвращаем также code_name
            else:
                log_event("FROM FRONT: Ошибка обработки файла")
                return None, None

def get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise):
    """
    processes the user"s request and returns a response
    """
    return asyncio.run(async_get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise))


with gr.Blocks() as app:
    gr.Markdown("## ЗАГРУЗКА ФАЙЛА ДЛЯ ОБРАБОТКИ", elem_id="title")
    current_time = round(get_timestamp())
    file_input = gr.File(label="загрузите файл", type="binary")
    anonymize_checkbox = gr.Checkbox(label="Анонимизировать имена", value=False)
    output_code_name = gr.Textbox(label="закодированные имена", interactive=False)
    save_datetime_checkbox = gr.Checkbox(label="Сохранять дату/время", value=False)
    max_len_context = gr.Slider(label="Выберите максимальную длину итогового текста", minimum=1000, maximum=15200, value=5550, step=10)
    time_choise = gr.Slider(
        minimum=round(current_time - 86400 * 28),
        maximum=current_time,
        step=60,
        value=round(current_time / 2),
        label="Выберите дату и время отсчёта начала чата")
    output_time_choise = gr.Textbox(label="Выбранное время", value=format_timestamp(time_choise.value))
    process_btn = gr.Button("запустить обработку файла")
    output_get = gr.File(label="скачайте результат в виде txt файла")

    time_choise.change(format_timestamp, time_choise, output_time_choise)
    process_btn.click(
        fn=get_resp, 
        inputs=[file_input, anonymize_checkbox, save_datetime_checkbox, max_len_context, time_choise],
        outputs=[output_get, output_code_name]
    )

delete_files("result.txt", "app.log")
log_event("===Запуск приложения===")
app.launch(server_name="0.0.0.0", server_port=7861)