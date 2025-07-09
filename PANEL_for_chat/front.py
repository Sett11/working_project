import gradio as gr
from hand_files import upload_and_update_status, delete_and_update_status, clear_all_files
from chat import chat_response
from logs import clear_logs, log_event


with gr.Blocks(title="Chat with File Upload", theme=gr.themes.Soft()) as demo:
    
    with gr.Column(visible=True, elem_id="chat_section") as chat_section:
        # Основной макет приложения после входа
        with gr.Row():
            # Левая панель - файлы
            with gr.Column(scale=1, min_width=200):
                with gr.Blocks():
                    gr.Markdown("## Файлы")
                    file_upload = gr.File(file_count="multiple", label="Загрузить файлы", interactive=True)
                    clear_files = gr.Button("Очистить все файлы")
                    gr.Markdown("### Поддерживаемые форматы:")
                    gr.Markdown("- TXT - текстовые файлы")
                    gr.Markdown("- PDF - документы PDF")
                    gr.Markdown("- DOCX - документы Microsoft Word")
                    gr.Markdown("- PPTX - презентации Microsoft PowerPoint")
                    gr.Markdown("**Максимальный размер:** 110 000 символов или 100 МБ")
            
            # Правая панель - чат
            with gr.Column(scale=3):
                with gr.Blocks():
                    gr.Markdown("## Чат с документами")
                    chatbot = gr.Chatbot(height=500)
                    msg = gr.Textbox(label="Ваш вопрос", placeholder="Задайте вопрос по загруженным документам...")
                    push_prompt = gr.Button("Отправить")
                    clear_chat = gr.Button("Очистить чат")
        
        # Нижняя панель - статус
        with gr.Row():
            with gr.Column():
                status = gr.Markdown("Загрузите документы и задайте вопросы для анализа содержимого.")

    file_upload.upload(
        upload_and_update_status,
        inputs=file_upload,
        outputs=status
    )
    
    file_upload.change(
        delete_and_update_status,
        inputs=file_upload,
        outputs=status
    )
    
    clear_files.click(
        clear_all_files,
        outputs=[file_upload, status]
    )

    push_prompt.click(
        lambda msg, history: (log_event("CHAT_MESSAGE", f"Message: {msg}"), 
                            history + [[msg, chat_response(msg, history)]])[1],
        [msg, chatbot],
        chatbot
    ).then(
        lambda: "",
        outputs=msg
    )
    
    msg.submit(
        lambda msg, history: (log_event("CHAT_MESSAGE", f"Message: {msg}"), 
                            history + [[msg, chat_response(msg, history)]])[1],
        [msg, chatbot],
        chatbot
    ).then(
        lambda: "",
        outputs=msg
    )
    
    clear_chat.click(
        lambda: (log_event("CLEAR_CHAT"), [])[1],
        outputs=chatbot
    ).then(
        lambda: ([], []),
        outputs=[chatbot, msg]
    )

clear_logs()
log_event("APP_START", "Application started")
demo.launch(server_name="localhost", server_port=7860, share=False, auth=("admin", "password123"))