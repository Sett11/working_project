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
import os
from typing import Optional
from utils.mylogger import Logger

logger = Logger(name=__name__, log_file="frontend.log")

# URL для backend API
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8001")

class AuthManager:
    """Менеджер аутентификации для Gradio интерфейса."""
    
    def __init__(self):
        self.token: Optional[str] = None
        self.username: Optional[str] = None
        self.user_id: Optional[int] = None
        self.auth_file = "/app/auth_data.json"  # Файл для сохранения данных аутентификации
        self._load_auth_data()  # Загружаем сохраненные данные при инициализации
    
    def _save_auth_data(self):
        """Сохранение данных аутентификации в файл."""
        try:
            auth_data = {
                "token": self.token,
                "username": self.username,
                "user_id": self.user_id
            }
            with open(self.auth_file, 'w', encoding='utf-8') as f:
                json.dump(auth_data, f, ensure_ascii=False, indent=2)
            logger.info("Данные аутентификации сохранены")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных аутентификации: {e}")
    
    def _load_auth_data(self):
        """Загрузка данных аутентификации из файла."""
        try:
            if os.path.exists(self.auth_file):
                with open(self.auth_file, 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                self.token = auth_data.get("token")
                self.username = auth_data.get("username")
                self.user_id = auth_data.get("user_id")
                if self.token and self.username and self.user_id:
                    logger.set_user_context(self.user_id)
                    logger.info(f"Данные аутентификации загружены для пользователя: {self.username}")
                    # Проверяем валидность токена
                    if not self._validate_token():
                        logger.warning("Загруженный токен недействителен, очищаем данные")
                        self.clear_auth_data()
                else:
                    logger.info("Файл аутентификации пуст или поврежден")
            else:
                logger.info("Файл аутентификации не найден")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных аутентификации: {e}")
    
    def _validate_token(self) -> bool:
        """Проверка валидности токена через API."""
        try:
            if not self.token:
                return False
            
            with httpx.Client() as client:
                response = client.get(
                    f"{BACKEND_URL}/api/auth/me",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ошибка при проверке токена: {e}")
            return False
    
    def set_auth_data(self, token: str, username: str, user_id: int):
        """Установка данных аутентификации."""
        self.token = token
        self.username = username
        self.user_id = user_id
        logger.set_user_context(user_id)
        logger.info(f"Пользователь аутентифицирован: {username}")
        self._save_auth_data()  # Сохраняем данные в файл
    
    def clear_auth_data(self):
        """Очистка данных аутентификации."""
        self.token = None
        self.username = None
        self.user_id = None
        logger.clear_user_context()
        logger.info("Пользователь вышел из системы")
        # Удаляем файл с данными аутентификации
        try:
            if os.path.exists(self.auth_file):
                os.remove(self.auth_file)
                logger.info("Файл аутентификации удален")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла аутентификации: {e}")
    
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


def register_user(username: str, password: str, secret_key: str) -> str:
    """
    Регистрация нового пользователя.
    
    Args:
        username: Логин пользователя
        password: Пароль
        secret_key: Секретный ключ
        
    Returns:
        str: Сообщение о результате
    """
    try:
        logger.info(f"Попытка регистрации пользователя: {username}")
        
        # Проверяем входные данные
        if not username or not password or not secret_key:
            return "❌ Все поля обязательны для заполнения"
        
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
            return f"✅ Пользователь {username} успешно зарегистрирован и вошел в систему!\n\nПереход к приложению...", "AUTH_SUCCESS"
        else:
            error_data = response.json()
            error_msg = error_data.get("detail", "Неизвестная ошибка")
            logger.warning(f"Ошибка регистрации: {error_msg}")
            return f"❌ Ошибка регистрации: {error_msg}"
            
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к backend при регистрации: {e}")
        return "❌ Ошибка подключения к серверу"
    except Exception as e:
        logger.error(f"Неожиданная ошибка при регистрации: {e}")
        return f"❌ Неожиданная ошибка: {str(e)}"


def login_user(username: str, password: str) -> str:
    """
    Вход пользователя в систему.
    
    Args:
        username: Логин пользователя
        password: Пароль
        
    Returns:
        str: Сообщение о результате
    """
    try:
        logger.info(f"Попытка входа пользователя: {username}")
        
        # Проверяем входные данные
        if not username or not password:
            return "❌ Логин и пароль обязательны"
        
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
            return f"✅ Добро пожаловать, {username}!\n\nПереход к приложению...", "AUTH_SUCCESS"
        else:
            error_data = response.json()
            error_msg = error_data.get("detail", "Неизвестная ошибка")
            logger.warning(f"Ошибка входа: {error_msg}")
            return f"❌ Ошибка входа: {error_msg}"
            
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к backend при входе: {e}")
        return "❌ Ошибка подключения к серверу"
    except Exception as e:
        logger.error(f"Неожиданная ошибка при входе: {e}")
        return f"❌ Неожиданная ошибка: {str(e)}"


def logout_user() -> str:
    """
    Выход пользователя из системы.
    
    Returns:
        str: Сообщение о результате
    """
    auth_manager.clear_auth_data()
    return "✅ Вы успешно вышли из системы"


def create_auth_interface() -> gr.Blocks:
    """
    Создание красивого интерфейса аутентификации с переключением режимов.
    
    Returns:
        gr.Blocks: Gradio интерфейс аутентификации
    """
    
    def switch_to_login():
        """Переключение на режим входа."""
        return (
            gr.update(visible=True),   # login_fields
            gr.update(visible=False),  # reg_fields
            gr.update(variant="primary"),  # login_btn
            gr.update(variant="secondary"),  # reg_btn
            "### Вход в систему",  # form_title
            "Войти",  # submit_btn
            "login"  # current_mode
        )
    
    def switch_to_register():
        """Переключение на режим регистрации."""
        return (
            gr.update(visible=False),  # login_fields
            gr.update(visible=True),   # reg_fields
            gr.update(variant="secondary"),  # login_btn
            gr.update(variant="primary"),  # reg_btn
            "### Регистрация",  # form_title
            "Зарегистрироваться",  # submit_btn
            "register"  # current_mode
        )
    
    def handle_auth(username, password, reg_username, reg_password, secret_key, mode):
        """Обработка аутентификации в зависимости от режима."""
        if mode == "login":
            result = login_user(username, password)
            if isinstance(result, tuple):
                message, status = result
                if status == "AUTH_SUCCESS":
                    # При успешной аутентификации возвращаем специальный статус
                    return message, "AUTH_SUCCESS"
                else:
                    return result
            else:
                return result, "AUTH_ERROR"
        else:
            # В режиме регистрации используем поля регистрации
            result = register_user(reg_username, reg_password, secret_key)
            if isinstance(result, tuple):
                message, status = result
                if status == "AUTH_SUCCESS":
                    # При успешной аутентификации возвращаем специальный статус
                    return message, "AUTH_SUCCESS"
                else:
                    return result
            else:
                return result, "AUTH_ERROR"
    
    def get_current_mode():
        """Получение текущего режима."""
        return "login"  # По умолчанию режим входа
    
    def clear_all_fields():
        """Очистка всех полей."""
        return "", "", "", "", "", ""  # username, password, reg_username, reg_password, secret_key, result
    
    with gr.Blocks(
        title="🔐 Аутентификация",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="gray",
            neutral_hue="slate"
        ),
        head="""
        <style>
        /* Принудительное скрытие стрелочек */
        * input::-webkit-outer-spin-button,
        * input::-webkit-inner-spin-button {
            -webkit-appearance: none !important;
            margin: 0 !important;
            display: none !important;
        }
        
        * input[type=text]::-webkit-outer-spin-button,
        * input[type=text]::-webkit-inner-spin-button {
            -webkit-appearance: none !important;
            margin: 0 !important;
            display: none !important;
        }
        
        * input {
            -moz-appearance: textfield !important;
        }
        
        /* Крупный логотип EVERIS */
        #everis-logo {
            color: white !important;
            font-size: 10rem !important;
            font-weight: 900 !important;
            margin: 2rem 0 !important;
            text-shadow: 0 15px 30px rgba(0,0,0,0.9) !important;
            letter-spacing: 0.8em !important;
            font-family: 'Arial Black', 'Arial', sans-serif !important;
            background: linear-gradient(135deg, #ffffff 0%, #f0f0f0 20%, #ffffff 50%, #e0e0e0 80%, #ffffff 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
            text-align: center !important;
            transform: scale(1.5) !important;
            animation: everis-glow 2s ease-in-out infinite alternate !important;
            display: block !important;
            line-height: 1.1 !important;
        }
        
        @keyframes everis-glow {
            from { 
                text-shadow: 0 15px 30px rgba(0,0,0,0.9), 0 0 60px rgba(255,255,255,0.7) !important;
                transform: scale(1.5) !important;
            }
            to { 
                text-shadow: 0 15px 30px rgba(0,0,0,0.9), 0 0 100px rgba(255,255,255,1) !important;
                transform: scale(1.55) !important;
            }
        }
        </style>
        """,
        css="""
        .auth-container {
            max-width: 500px;
            margin: 0 auto;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        #everis-logo {
            color: white !important;
            font-size: 8rem !important;
            font-weight: 900 !important;
            margin-bottom: 2rem !important;
            text-shadow: 0 12px 24px rgba(0,0,0,0.9) !important;
            letter-spacing: 0.6em !important;
            font-family: 'Arial Black', 'Arial', sans-serif !important;
            background: linear-gradient(135deg, #ffffff 0%, #f0f0f0 20%, #ffffff 50%, #e0e0e0 80%, #ffffff 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
            text-align: center !important;
            transform: scale(1.4) !important;
            animation: glow 2s ease-in-out infinite alternate !important;
            display: block !important;
            line-height: 1.2 !important;
        }
        @keyframes glow {
            from { 
                text-shadow: 0 12px 24px rgba(0,0,0,0.9), 0 0 50px rgba(255,255,255,0.6) !important;
                transform: scale(1.4) !important;
            }
            to { 
                text-shadow: 0 12px 24px rgba(0,0,0,0.9), 0 0 80px rgba(255,255,255,0.9) !important;
                transform: scale(1.45) !important;
            }
        }
        .auth-subtitle {
            color: rgba(255,255,255,0.8);
            font-size: 1.1rem;
        }
        .mode-buttons {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .form-container {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .form-title {
            text-align: center;
            font-size: 1.5rem;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 1.5rem;
        }
        .submit-btn {
            width: 100%;
            height: 50px;
            font-size: 1.1rem;
            font-weight: 600;
            border-radius: 10px;
            margin-top: 1rem;
        }
        .result-box {
            margin-top: 1rem;
            border-radius: 10px;
        }
        
        /* Агрессивное скрытие стрелочек для всех input полей */
        .gradio-container input::-webkit-outer-spin-button,
        .gradio-container input::-webkit-inner-spin-button,
        .gradio-container input[type="text"]::-webkit-outer-spin-button,
        .gradio-container input[type="text"]::-webkit-inner-spin-button,
        .gradio-container input[type="number"]::-webkit-outer-spin-button,
        .gradio-container input[type="number"]::-webkit-inner-spin-button,
        .gradio-container textarea::-webkit-outer-spin-button,
        .gradio-container textarea::-webkit-inner-spin-button {
            -webkit-appearance: none !important;
            margin: 0 !important;
            display: none !important;
        }
        
        .gradio-container input,
        .gradio-container input[type="text"],
        .gradio-container input[type="number"],
        .gradio-container textarea {
            -moz-appearance: textfield !important;
            -webkit-appearance: none !important;
        }
        
        /* Дополнительное скрытие для всех input элементов */
        input::-webkit-outer-spin-button,
        input::-webkit-inner-spin-button,
        input[type="text"]::-webkit-outer-spin-button,
        input[type="text"]::-webkit-inner-spin-button {
            -webkit-appearance: none !important;
            margin: 0 !important;
            display: none !important;
        }
        
        input,
        input[type="text"] {
            -moz-appearance: textfield !important;
            -webkit-appearance: none !important;
        }
        """
    ) as auth_interface:
        
        with gr.Column(elem_classes="auth-container"):
            # Заголовок
            with gr.Column(elem_classes="auth-header"):
                gr.HTML("""
                    <div class="everis-logo" id="everis-logo">EVERIS</div>
                    <div class="auth-subtitle">Добро пожаловать в систему</div>
                """)
            
            # Кнопки переключения режимов
            with gr.Row(elem_classes="mode-buttons"):
                login_mode_btn = gr.Button(
                    "Вход", 
                    variant="primary", 
                    size="lg",
                    elem_id="login_mode_btn"
                )
                reg_mode_btn = gr.Button(
                    "Регистрация", 
                    variant="secondary", 
                    size="lg",
                    elem_id="reg_mode_btn"
                )
            
            # Форма
            with gr.Column(elem_classes="form-container"):
                form_title = gr.Markdown("### Вход в систему", elem_classes="form-title")
                
                # Поля для входа
                with gr.Column(visible=True, elem_id="login_fields") as login_fields:
                    username = gr.Textbox(
                        label="👤 Логин",
                        placeholder="Введите ваш логин",
                        show_label=True,
                        container=True,
                        elem_id="login-username"
                    )
                    
                    password = gr.Textbox(
                        label="🔒 Пароль",
                    placeholder="Введите пароль",
                    type="password",
                        show_label=True,
                        container=True
                    )
                
                # Поля для регистрации
                with gr.Column(visible=False, elem_id="reg_fields") as reg_fields:
                    reg_username = gr.Textbox(
                        label="👤 Логин",
                        placeholder="Придумайте логин",
                        show_label=True,
                        container=True,
                        elem_id="reg-username"
                    )
                    
                    reg_password = gr.Textbox(
                        label="🔒 Пароль",
                        placeholder="Придумайте пароль",
                        type="password",
                        show_label=True,
                        container=True
                    )
                    
                    secret_key = gr.Textbox(
                        label="🔑 Секретный ключ",
                        placeholder="Введите секретный ключ",
                        type="password",
                    show_label=True,
                        container=True
                    )
                
                # Кнопка отправки
                submit_btn = gr.Button(
                    "Войти",
                    variant="primary",
                    size="lg",
                    elem_classes="submit-btn"
                )
                
                # Результат
                auth_result = gr.Textbox(
                    label="Результат",
                    interactive=False,
                    visible=True,
                    lines=3,
                    elem_classes="result-box"
                )
        
        # Состояние для отслеживания текущего режима
        current_mode = gr.State("login")
        
        # Обработчики событий
        login_mode_btn.click(
            fn=switch_to_login,
            outputs=[login_fields, reg_fields, login_mode_btn, reg_mode_btn, form_title, submit_btn, current_mode]
        )
        
        reg_mode_btn.click(
            fn=switch_to_register,
            outputs=[login_fields, reg_fields, login_mode_btn, reg_mode_btn, form_title, submit_btn, current_mode]
        )
        
        # Скрытое поле для статуса аутентификации
        auth_status_hidden = gr.State("")
        
        # Обработка отправки формы
        submit_btn.click(
            fn=handle_auth,
            inputs=[username, password, reg_username, reg_password, secret_key, current_mode],
            outputs=[auth_result, auth_status_hidden],
            show_progress=True
        ).then(
            fn=clear_all_fields,
            outputs=[username, password, reg_username, reg_password, secret_key, auth_result]
        )
    
        # Возвращаем auth_status_hidden для использования в основном интерфейсе
        return auth_interface, auth_status_hidden


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
