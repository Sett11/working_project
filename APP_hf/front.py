import gradio as gr
import requests

def get_resp(file):
    URL = 'http://127.0.0.1:8000/upload_file/'
    with open(file.name, 'rb') as f:
        files = {'file': (file.name, f)}
        out = requests.post(URL, files=files)
    return out.json()

with gr.Blocks() as app:
    gr.Markdown("## ЗАГРУЗКА ФАЙЛА ДЛЯ ОБРАБОТКИ", elem_id="title")

    input_get = gr.File(label="загрузите файл", type="filepath")
    get_btn = gr.Button('запустить обработку')
    output_get = gr.File(label='скачайте результат в виде txt файла', type='filepath')
    get_btn.click(fn=get_resp, inputs=input_get, outputs=output_get)

app.launch(server_name="0.0.0.0", server_port=7860)