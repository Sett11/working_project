import gradio as gr
from hand_files import (
    update_file_display_sync,
    handle_file_delete_sync
)
from chat import chat_response, chat_history
from authenticate import login
from logs import clear_logs, log_event


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
            
            # Правая панель - чат
            with gr.Column(scale=3):
                with gr.Blocks():
                    gr.Markdown("## Чат")
                    chatbot = gr.Chatbot(height=500)
                    msg = gr.Textbox(label="Ваше сообщение")
                    clear_chat = gr.Button("Очистить чат")
        
        # Нижняя панель - статус
        with gr.Row():
            status = gr.Markdown()
    
    # Обработчики событий
    login_btn.click(
        login,
        inputs=[username, password],
        outputs=[login_section, chat_section, login_status]
    )
    
    file_upload.upload(
        update_file_display_sync,
        inputs=file_upload,
        outputs=file_output
    )
    
    file_upload.change(
        handle_file_delete_sync,
        inputs=file_upload,
        outputs=file_output
    )
    
    clear_files.click(
        lambda: (handle_file_delete_sync([]), None),
        outputs=[file_output, file_upload]
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
    clear_logs()  # Очищаем старые логи перед запуском
    log_event("APP_START", "Application started")
    demo.launch(server_name="0.0.0.0", server_port=7860)