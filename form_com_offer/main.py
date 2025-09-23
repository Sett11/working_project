"""
Основной файл для запуска front-приложения.

Этот скрипт служит точкой входа для всего приложения.
Он импортирует готовый интерфейс из модуля `front.front` и запускает его,
делая веб-интерфейс доступным в локальной сети.
"""
from front.new_front import interface
from utils.mylogger import Logger

# Инициализируем логгер для main.py
frontend_logger = Logger(name=__name__, log_file="frontend.log")
import nest_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

nest_asyncio.apply()

# Настройки для контейнера
SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))

# Основная точка входа в приложение.
# При запуске этого файла как основного скрипта, выполняется код ниже.

if __name__ == "__main__":
    
    # Логируем начало процесса запуска веб-интерфейса.
    frontend_logger.info("Запуск front интерфейса...")

    # Запускаем веб-сервер front.
    # server_name="0.0.0.0" делает приложение доступным для других устройств в той же сети.
    # server_port=7860 указывает порт, на котором будет работать приложение.
    try:
        interface.launch(
            server_name=SERVER_NAME, 
            server_port=SERVER_PORT,
            share=True,
            quiet=False,
            inbrowser=False,
            show_error=True,
            prevent_thread_lock=False,
            allowed_paths=["/app"]
        )
        frontend_logger.info("front интерфейс успешно запущен.")
    except Exception as e:
        frontend_logger.error(f"Произошла ошибка при запуске front интерфейса: {e}", exc_info=True)
    finally:
        # Этот лог будет записан после остановки сервера (например, по Ctrl+C).
        frontend_logger.info("front интерфейс остановлен.")
