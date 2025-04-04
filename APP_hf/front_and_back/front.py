import gradio as gr
import aiohttp
import asyncio
import os
from hand_logs.mylogger import Logger, LOG_FILE
import logging

logger = Logger('app_logger', LOG_FILE, level=logging.INFO)
files_queue = []

def log_event(message):
    logger.info(f"FROM FRONT: {message}")

def update_slider(time_choise):
    return time_choise

async def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            log_event(f'Файл {file_path} удалён.')
        else:
            log_event(f'Файл {file_path} не найден.')
    except Exception as e:
        log_event(f'Ошибка удаления файла {file_path}: {e}')

def handle_download():
    current_file_path = files_queue.pop() if files_queue else None
    if current_file_path:
        log_event(f"Файл {current_file_path} отправлен на скачивание, готовим удаление...")
        asyncio.run(delete_file(current_file_path))

async def async_get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise):
    if file_bytes is None:
        log_event("Файл не загружен")
        return None, None
    
    # URL = "http://localhost:8000/upload_file/" # для запуска на локальной машине
    URL = "http://backend:8000/upload_file/" # для сборки в docker
    data = aiohttp.FormData()
    file_name = "res_files/" + os.urandom(4).hex() + ".txt"
    files_queue.append(file_name)
    
    data.add_field("anonymize_names", str(anonymize_names))
    data.add_field("save_datetime", str(save_datetime))
    data.add_field("max_len_context", str(max_len_context))
    data.add_field("time_choise", str(time_choise))
    data.add_field("file", file_bytes)
    
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, data=data) as response:
            out = await response.json()
            if response.status == 200 and (r := out.get("result")):
                with open(file_name, "w", encoding="utf8") as result_file:
                    result_file.write(r)
                code_name = out.get("code_name", {})
                return file_name, "\n".join(f"{id}->{name}" for id, name in code_name.items())
            else:
                log_event("Ошибка обработки файла")
                return None, None

def get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise):
    log_event(f"Параметры: {anonymize_names}, {save_datetime}, {max_len_context}, {time_choise}")
    return asyncio.run(async_get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise))

with gr.Blocks() as app:
    gr.Markdown("## ЗАГРУЗКА ФАЙЛА ДЛЯ ОБРАБОТКИ")
    file_input = gr.File(label="Загрузите файл", type="binary")
    anonymize_checkbox = gr.Checkbox(label="Анонимизировать имена", value=False)
    output_code_name = gr.Textbox(label="Закодированные имена", interactive=False)
    save_datetime_checkbox = gr.Checkbox(label="Сохранять дату/время", value=False)
    max_len_context = gr.Slider(
        minimum=1000,
        maximum=50000,
        value=25000,
        step=100,
        label="Макс. длина итогового контента (в токенах)"
    )
    time_choise = gr.Slider(
        minimum=0,
        maximum=480,
        step=1,
        value=24,
        label="Время отсчёта от конца чата (в часах)"
    )
    output_time_choise = gr.Textbox(label="Начинаем с...", value=time_choise.value)
    process_btn = gr.Button("Запустить обработку файла")
    output_get = gr.File(label="Скачайте результат (txt)")

    time_choise.change(
        fn=update_slider,
        inputs=time_choise,
        outputs=output_time_choise
    )
    
    process_btn.click(
        fn=get_resp,
        inputs=[file_input, anonymize_checkbox, save_datetime_checkbox, max_len_context, time_choise],
        outputs=[output_get, output_code_name]
    )
    
    output_get.download(
        fn=handle_download,
        inputs=[],
        outputs=[]
    )

app.launch(server_name="0.0.0.0", server_port=7861)