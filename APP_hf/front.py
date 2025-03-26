import gradio as gr
import requests
import datetime
from custom_print import custom_print
from delete_files import delete_files


def detect_file_type(file_content):
    """
    Определяет тип файла по его содержимому
    Возвращает: "json", "html", "txt" или None если тип не определен
    """
    try:
        # Пробуем декодировать как JSON
        content_str = file_content.decode("utf-8")
        if content_str.strip().startswith("{") or content_str.strip().startswith("["):
            return "json"
        
        # Проверяем на HTML
        if "<html" in content_str.lower() or "<!DOCTYPE html" in content_str.lower():
            return "html"
        
        # Если не JSON и не HTML, считаем текстовым файлом
        return "txt"
    except UnicodeDecodeError:
        return


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


def get_resp(file_bytes, anonymize_names, save_datetime, max_len_context, time_choise):
    """
    processes the user"s request and returns a response
    """
    delete_files("result.txt") # удаляем старый файл результата обработки при любом новом запросе - даже некорректном

    if file_bytes is None:
        custom_print("Пользовательский файл не был загружен")
        return None, None
    
    URL = "http://backend:8000/upload_file/" # для запуска в Docker
    # URL = "http://localhost:8000/upload_file/" # для запуска на локальной машине

    # Определяем тип файла по содержимому
    file_type = detect_file_type(file_bytes)
    if file_type is None:
        custom_print("Не удалось определить тип файла")
        return None, None
    
    # Формируем имя файла с правильным расширением
    filename = f"uploaded_file.{file_type}"
    
    files = {"file": (filename, file_bytes)}
    data = {"anonymize_names": anonymize_names, "save_datetime": save_datetime, "max_len_context": max_len_context, "time_choise": format_timestamp(time_choise)}
    out = requests.post(URL, files=files, data=data)
        
    if out.status_code == 200 and (r:=out.json().get("result")): # может вернуть пустую строку
        with open("result.txt", "w", encoding="utf8") as result_file:
            result_file.write(r)

        code_name = out.json().get("code_name", "")  # получаем словарь code_name из ответа
        return "result.txt", "\n".join(f"{id}->{name}" for id, name in code_name.items()) if code_name else ""  # возвращаем также code_name
    else:
        custom_print("Ошибка обработки файла")
        return None, None


with gr.Blocks() as app:
    delete_files("app_logs.txt", "result.txt") # удаляем все старые файлы перед запуском приложения
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


app.launch(server_name="0.0.0.0", server_port=7861)