import gradio as gr
import requests
from custom_print import custom_print
from delete_files import delete_files


def get_resp(file_path, anonymize_names, save_datetime, max_len_context):

    if file_path == 'mock.txt':
        custom_print('Пользовательский файл не был загружен')
        return
    
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

# js_code = """
# <script>
#     window.onbeforeunload = function() {
#         fetch('/reload', { method: 'POST' });
#     };
# </script>
# """


with gr.Blocks() as app:
    gr.Markdown('## ЗАГРУЗКА ФАЙЛА ДЛЯ ОБРАБОТКИ', elem_id='title')

    file_input = gr.File(label='загрузите файл', type='filepath', value='mock.txt')
    anonymize_checkbox = gr.Checkbox(label='Анонимизировать имена', value=True)
    save_datetime_checkbox = gr.Checkbox(label='Сохранять дату/время', value=False)
    max_len_context = gr.Slider(label='Выберите максимальную длину итогового текста', minimum=1000, maximum=15200, value=5550, step=10)
    # date_starting = gr.Slider('Выберите дату начала отсчёта беседы')
    process_btn = gr.Button('запустить обработку файла')
    output_get = gr.File(label='скачайте результат в виде txt файла')

    process_btn.click(
        fn=get_resp, 
        inputs=[file_input, anonymize_checkbox, save_datetime_checkbox, max_len_context],
        outputs=output_get
    )

app.launch(server_name='0.0.0.0', server_port=7860)