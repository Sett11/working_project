"""
Модуль аутентификации для Gradio интерфейса.

Содержит:
- Интерфейс входа и регистрации
- Управление токенами аутентификации
- Интеграция с backend API
"""
import gradio as gr
import httpx
import json
from typing import Optional, Tuple
from utils.mylogger import Logger

logger = Logger(name=__name__, log_file="frontend.log")

# URL для backend API
BACKEND_URL = "http://backend:8001"

class AuthManager:
    """Менеджер аутентификации для Gradio интерфейса."""
    
    def __init__(self):
        self.token: Optional[str] = None
        self.username: Optional[str] = None
        self.user_id: Optional[int] = None
    
    def set_auth_data(self, token: str, username: str, user_id: int):
        """Установка данных аутентификации."""
        self.token = token
        self.username = username
        self.user_id = user_id
        logger.set_user_context(user_id)
        logger.info(f"Пользователь аутентифицирован: {username}")
    
    def clear_auth_data(self):
        """Очистка данных аутентификации."""
        self.token = None
        self.username = None
        self.user_id = None
        logger.clear_user_context()
        logger.info("Пользователь вышел из системы")
    
    def is_authenticated(self) -> bool:
        """Проверка аутентификации."""
        return self.token is not None
    
    def get_auth_headers(self) -> dict:
        """Получение заголовков для аутентифицированных запросов."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

# Глобальный экземпляр менеджера аутентификации
auth_manager = AuthManager()


def register_user(username: str, password: str, secret_key: str) -> Tuple[str, bool]:
    """
    Регистрация нового пользователя.
    
    Args:
        username: Логин пользователя
        password: Пароль
        secret_key: Секретный ключ
        
    Returns:
        Tuple[str, bool]: (сообщение, успех)
    """
    try:
        logger.info(f"Попытка регистрации пользователя: {username}")
        
        # Проверяем входные данные
        if not username or not password or not secret_key:
            return "Все поля обязательны для заполнения", False
        
        # Отправляем запрос на регистрацию
        with httpx.Client() as client:
            response = client.post(
                f"{BACKEND_URL}/api/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "secret_key": secret_key
                },
                timeout=10.0
            )
        
        if response.status_code == 200:
            data = response.json()
            auth_manager.set_auth_data(
                token=data["token"],
                username=data["user"]["username"],
                user_id=data["user"]["id"]
            )
            logger.info(f"Пользователь успешно зарегистрирован: {username}")
            return f"✅ Пользователь {username} успешно зарегистрирован и вошел в систему!\n\nНажмите 'Проверить статус' для перехода к приложению.", True
        else:
            error_data = response.json()
            error_msg = error_data.get("detail", "Неизвестная ошибка")
            logger.warning(f"Ошибка регистрации: {error_msg}")
            return f"❌ Ошибка регистрации: {error_msg}", False
            
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к backend при регистрации: {e}")
        return "❌ Ошибка подключения к серверу", False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при регистрации: {e}")
        return f"❌ Неожиданная ошибка: {str(e)}", False


def login_user(username: str, password: str) -> Tuple[str, bool]:
    """
    Вход пользователя в систему.
    
    Args:
        username: Логин пользователя
        password: Пароль
        
    Returns:
        Tuple[str, bool]: (сообщение, успех)
    """
    try:
        logger.info(f"Попытка входа пользователя: {username}")
        
        # Проверяем входные данные
        if not username or not password:
            return "❌ Логин и пароль обязательны", False
        
        # Отправляем запрос на вход
        with httpx.Client() as client:
            response = client.post(
                f"{BACKEND_URL}/api/auth/login",
                json={
                    "username": username,
                    "password": password
                },
                timeout=10.0
            )
        
        if response.status_code == 200:
            data = response.json()
            auth_manager.set_auth_data(
                token=data["token"],
                username=data["user"]["username"],
                user_id=data["user"]["id"]
            )
            logger.info(f"Пользователь успешно вошел: {username}")
            return f"✅ Добро пожаловать, {username}!\n\nНажмите 'Проверить статус' для перехода к приложению.", True
        else:
            error_data = response.json()
            error_msg = error_data.get("detail", "Неизвестная ошибка")
            logger.warning(f"Ошибка входа: {error_msg}")
            return f"❌ Ошибка входа: {error_msg}", False
            
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к backend при входе: {e}")
        return "❌ Ошибка подключения к серверу", False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при входе: {e}")
        return f"❌ Неожиданная ошибка: {str(e)}", False


def logout_user() -> Tuple[str, bool]:
    """
    Выход пользователя из системы.
    
    Returns:
        Tuple[str, bool]: (сообщение, успех)
    """
    auth_manager.clear_auth_data()
    return "Вы успешно вышли из системы", True


def create_auth_interface() -> gr.Blocks:
    """
    Создание интерфейса аутентификации.
    
    Returns:
        gr.Blocks: Gradio интерфейс аутентификации
    """
    
    def clear_fields():
        """Очистка полей после успешной аутентификации."""
        return "", "", "", "", ""  # login_username, login_password, reg_username, reg_password, reg_secret_key
    
    with gr.Blocks(title="Аутентификация") as auth_interface:
        gr.Markdown("# 🔐 Система аутентификации")
        
        # Общий результат для отображения сообщений
        auth_result = gr.Textbox(
            label="Результат",
            interactive=False,
            visible=True,
            lines=2
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Вход в систему")
                
                login_username = gr.Textbox(
                    label="Логин",
                    placeholder="Введите логин",
                    show_label=True
                )
                
                login_password = gr.Textbox(
                    label="Пароль",
                    placeholder="Введите пароль",
                    type="password",
                    show_label=True
                )
                
                login_btn = gr.Button("Войти", variant="primary")
            
            with gr.Column(scale=1):
                gr.Markdown("### Регистрация")
                
                reg_username = gr.Textbox(
                    label="Логин",
                    placeholder="Введите логин",
                    show_label=True
                )
                
                reg_password = gr.Textbox(
                    label="Пароль",
                    placeholder="Введите пароль",
                    type="password",
                    show_label=True
                )
                
                reg_secret_key = gr.Textbox(
                    label="Секретный ключ",
                    placeholder="Введите секретный ключ",
                    type="password",
                    show_label=True
                )
                
                reg_btn = gr.Button("Зарегистрироваться", variant="secondary")
        
        # Обработчики событий
        login_btn.click(
            fn=login_user,
            inputs=[login_username, login_password],
            outputs=[auth_result],
            show_progress=True
        ).then(
            fn=clear_fields,
            outputs=[login_username, login_password, reg_username, reg_password, reg_secret_key]
        )
        
        reg_btn.click(
            fn=register_user,
            inputs=[reg_username, reg_password, reg_secret_key],
            outputs=[auth_result],
            show_progress=True
        ).then(
            fn=clear_fields,
            outputs=[login_username, login_password, reg_username, reg_password, reg_secret_key]
        )
    
    return auth_interface


def get_auth_status() -> str:
    """
    Получение статуса аутентификации.
    
    Returns:
        str: Статус аутентификации
    """
    if auth_manager.is_authenticated():
        return f"Авторизован как: {auth_manager.username}"
    return "Не авторизован"


def get_auth_manager() -> AuthManager:
    """
    Получение менеджера аутентификации.
    
    Returns:
        AuthManager: Менеджер аутентификации
    """
    return auth_manager
