import gradio as gr
import requests
import datetime
from custom_print import custom_print
from delete_files import delete_files


def format_timestamp(timestamp):
    """
    returns a timestamp formatted as a string
    """
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')


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


def get_resp(file_path, anonymize_names, save_datetime, max_len_context, time_choise):
    """
    processes the user's request and returns a response
    """

    if file_path is None:
        custom_print('Пользовательский файл не был загружен')
        return
    
    URL = 'http://127.0.0.1:8000/upload_file/'
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_path, f)}
        data = {'anonymize_names': anonymize_names, 'save_datetime': save_datetime, 'max_len_context': max_len_context, 'time_choise': format_timestamp(time_choise)}
        out = requests.post(URL, files=files, data=data)
        
    if out.status_code == 200:
        with open('result.txt', 'wb') as result_file:
            result_file.write(out.content)
        return 'result.txt'
    else:
        return 'Error processing file'


with gr.Blocks() as app:
    delete_files('result.txt', 'app_logs.txt') # удаляем старые файлы перед запуском приложения
    gr.Markdown('## ЗАГРУЗКА ФАЙЛА ДЛЯ ОБРАБОТКИ', elem_id='title')

    current_time = round(get_timestamp())
    file_input = gr.File(label='загрузите файл', type='filepath')
    anonymize_checkbox = gr.Checkbox(label='Анонимизировать имена', value=True)
    save_datetime_checkbox = gr.Checkbox(label='Сохранять дату/время', value=False)
    max_len_context = gr.Slider(label='Выберите максимальную длину итогового текста', minimum=1000, maximum=15200, value=5550, step=10)
    time_choise = gr.Slider(
        minimum=round(current_time - 86400 * 28),
        maximum=current_time,
        step=60,
        value=current_time,
        label="Выберите дату и время отсчёта начала чата")
    output_time_choise = gr.Textbox(label="Выбранное время", value=format_timestamp(time_choise.value))
    process_btn = gr.Button('запустить обработку файла')
    output_get = gr.File(label='скачайте результат в виде txt файла')

    time_choise.change(format_timestamp, time_choise, output_time_choise)
    process_btn.click(
        fn=get_resp, 
        inputs=[file_input, anonymize_checkbox, save_datetime_checkbox, max_len_context, time_choise],
        outputs=output_get
    )


app.launch(server_name='0.0.0.0', server_port=7860)