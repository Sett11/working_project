import gradio as gr
import requests
from delete_files import delete_files


def get_resp(file_path, anonymize_names, save_datetime, max_len_context):
    URL = 'http://127.0.0.1:8000/upload_file/'
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_path, f)}
        data = {'anonymize_names': anonymize_names, 'save_datetime': save_datetime, 'max_len_context': max_len_context}
        out = requests.post(URL, files=files, data=data)
        
    if out.status_code == 200:
        with open('result.txt', 'wb') as result_file:
            result_file.write(out.content)
        return 'result.txt'
    else:
        return 'Error processing file'


delete_files('result.txt', 'app_logs.txt')


with gr.Blocks() as app:
    gr.Markdown('## ЗАГРУЗКА ФАЙЛА ДЛЯ ОБРАБОТКИ', elem_id='title')

    file_input = gr.File(label='загрузите файл', type='filepath')
    anonymize_checkbox = gr.Checkbox(label='Анонимизация имён', value=True)
    save_datetime_checkbox = gr.Checkbox(label='Сохранение даты/времени', value=False)
    max_len_context = gr.Slider(label='Выберите максимальную длину текста', minimum=0, maximum=15200, value=5000)
    process_btn = gr.Button('запустить обработку')
    output_get = gr.File(label='скачайте результат в виде txt файла')

    process_btn.click(
        fn=get_resp, 
        inputs=[file_input, anonymize_checkbox, save_datetime_checkbox, max_len_context],
        outputs=output_get
    )

app.launch(server_name='0.0.0.0', server_port=7860)