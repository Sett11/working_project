import gradio as gr
from hand_files import (
    upload_and_update_status,
    delete_and_update_status,
    clear_all_files
)
from chat import chat_response, chat_history
from authenticate import login
from logs import clear_logs, log_event
import os


with gr.Blocks(title="Chat with File Upload", theme=gr.themes.Soft()) as demo:
    # Состояние для хранения информации о входе
    logged_in = gr.State(False)
    
    with gr.Column(visible=True, elem_id="login_section") as login_section:
        with gr.Blocks():
            gr.Markdown("## Вход в систему")
            username = gr.Textbox(label="Логин", placeholder="admin")
            password = gr.Textbox(label="Пароль", type="password", placeholder="password123")
            login_btn = gr.Button("Войти")
            login_status = gr.Markdown()
    
    with gr.Column(visible=False, elem_id="chat_section") as chat_section:
        # Основной макет приложения после входа
        with gr.Row():
            # Левая панель - файлы
            with gr.Column(scale=1, min_width=200):
                with gr.Blocks():
                    gr.Markdown("## Файлы")
                    file_output = gr.Textbox(label="Загруженные файлы", lines=10, value="Нет загруженных файлов")
                    file_upload = gr.File(file_count="multiple", label="Загрузить файлы", interactive=True)
                    clear_files = gr.Button("Очистить все файлы")
                    gr.Markdown("### Поддерживаемые форматы:")
                    gr.Markdown("- TXT - текстовые файлы")
                    gr.Markdown("- PDF - документы PDF")
                    gr.Markdown("- DOCX - документы Microsoft Word")
                    gr.Markdown("- PPTX - презентации Microsoft PowerPoint")
                    gr.Markdown("**Максимальный размер:** 100 000 символов")
            
            # Правая панель - чат
            with gr.Column(scale=3):
                with gr.Blocks():
                    gr.Markdown("## Чат с документами")
                    chatbot = gr.Chatbot(height=500)
                    msg = gr.Textbox(label="Ваш вопрос", placeholder="Задайте вопрос по загруженным документам...")
                    clear_chat = gr.Button("Очистить чат")
        
        # Нижняя панель - статус
        with gr.Row():
            with gr.Column():
                status = gr.Markdown("Загрузите документы и задайте вопросы для анализа содержимого.")
    
    # Обработчики событий
    login_btn.click(
        login,
        inputs=[username, password],
        outputs=[login_section, chat_section, login_status]
    )
    
    file_upload.upload(
        upload_and_update_status,
        inputs=file_upload,
        outputs=[file_output, status]
    )
    
    file_upload.change(
        delete_and_update_status,
        inputs=file_upload,
        outputs=[file_output, status]
    )
    
    clear_files.click(
        clear_all_files,
        outputs=[file_output, file_upload, status]
    )
    
    msg.submit(
        lambda msg, history: (log_event("CHAT_MESSAGE", f"Message: {msg}"), chat_response(msg, history))[1],
        [msg, chatbot],
        chatbot
    ).then(
        lambda: "",
        outputs=msg
    )
    
    clear_chat.click(
        lambda: (log_event("CLEAR_CHAT"), [])[1],
        outputs=chatbot
    )

if __name__ == "__main__":
    # Создаем папку для загруженных файлов, если её нет
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        
    clear_logs()  # Очищаем старые логи перед запуском
    log_event("APP_START", "Application started")
    server_ip = os.environ.get("SERVER_IP", "0.0.0.0")
    demo.launch(server_name=server_ip, server_port=7860)