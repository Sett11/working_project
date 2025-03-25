from typing import Tuple
import gradio as gr
from logs import log_event


USER_CREDENTIALS = {"admin": "password123", "user": "123456"} # Хардкодные учетные данные

def login(username: str, password: str):
    """Обработчик входа в систему"""
    success, message = authenticate(username, password)
    log_event("LOGIN", f"User: {username}, Success: {success}")
    if success:
        return gr.update(visible=False), gr.update(visible=True), message
    return gr.update(visible=True), gr.update(visible=False), message

def authenticate(username: str, password: str) -> Tuple[bool, str]:
    """Проверка учетных данных"""
    if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
        return True, f"Добро пожаловать, {username}!"
    return False, "Неверный логин или пароль"