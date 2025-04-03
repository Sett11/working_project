import gradio as gr
import aiohttp
import asyncio
import os
import time
from logs import clear_logs, log_event as log_event_hf
from delete_files import delete_file

files_queue = []

def log_event(message):
    log_event_hf(f"FROM FRONT: {message}")

def update_slider(time_choise):
    return time_choise

async def async_get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise):
    if file_bytes is None:
        log_event("Пользовательский файл не был загружен")
        return None, None
    log_event(f"Размер загружаемого файла: {len(file_bytes)} байт")
    # URL = "http://backend:8000/upload_file/" # для запуска в Docker
    URL = "http://localhost:8000/upload_file/" # для запуска на локальной машине
    data = aiohttp.FormData()  # Создаем объект FormData
    file_name = "res_files/" + os.urandom(4).hex() + ".txt"
    files_queue.append(file_name)
    data.add_field("anonymize_names", str(anonymize_names))
    data.add_field("save_datetime", str(save_datetime))
    data.add_field("max_len_context", str(max_len_context))
    data.add_field("time_choise", str(time_choise))
    data.add_field("file", file_bytes) # Добавляем файл в FormData
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, data=data) as response:
            out = await response.json()  # Получаем JSON-ответ
            if response.status == 200 and (r := out.get("result")):  # Проверяем статус ответа
                with open(file_name, "w", encoding="utf8") as result_file:
                    result_file.write(r)
                code_name = out.get("code_name", {})  # получаем словарь code_name из ответа
                return file_name, "\n".join(f"{id}->{name}" for id, name in code_name.items()) if code_name else ""  # возвращаем также code_name
            else:
                log_event("FROM FRONT: Ошибка обработки файла")
                return None, None

def get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise):
    log_event(f"Параметры обрабтки: {anonymize_names}, {save_datetime}, {max_len_context}, {time_choise}")
    return asyncio.run(async_get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise))

with gr.Blocks() as app:
    gr.Markdown("## ЗАГРУЗКА ФАЙЛА ДЛЯ ОБРАБОТКИ", elem_id="title")
    file_input = gr.File(label="загрузите файл", type="binary")
    anonymize_checkbox = gr.Checkbox(label="Анонимизировать имена", value=False)
    output_code_name = gr.Textbox(label="закодированные имена", interactive=False)
    save_datetime_checkbox = gr.Checkbox(label="Сохранять дату/время", value=False)
    max_len_context = gr.Slider(
            minimum=5,
            maximum=100,
            value=50,
            step=1,
            label="Выберите максимальную длину итогового текста в % от общего количества символов в чате - считать будем с конца чата")
    time_choise = gr.Slider(
        minimum=0,
        maximum=480,
        step=1,
        value=24,
        label="Выберите время отсчёта итогового текста от конца чата - в часах")
    output_time_choise = gr.Textbox(label="Начинаем с...", value=time_choise.value)
    process_btn = gr.Button("запустить обработку файла")
    output_get = gr.File(label="скачайте результат в виде txt файла")

    time_choise.change(update_slider, time_choise, output_time_choise)
    process_btn.click(
        fn=get_resp, 
        inputs=[file_input, anonymize_checkbox, save_datetime_checkbox, max_len_context, time_choise],
        outputs=[output_get, output_code_name])
    output_get.download(delete_file, inputs=output_get, outputs=[])

clear_logs()
app.launch(server_name="0.0.0.0", server_port=7861)