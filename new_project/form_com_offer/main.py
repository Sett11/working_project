"""
Основной файл для запуска Gradio-приложения.

Этот скрипт служит точкой входа для всего приложения.
Он импортирует готовый интерфейс из модуля `front.front` и запускает его,
делая веб-интерфейс доступным в локальной сети.
"""
from front.front import interface, logger
import nest_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

login = os.getenv("GRADIO_LOGIN")
password = os.getenv("GRADIO_PASSWORD")

nest_asyncio.apply()

# Основная точка входа в приложение.
# При запуске этого файла как основного скрипта, выполняется код ниже.

if __name__ == "__main__":
    # Логируем начало процесса запуска веб-интерфейса.
    logger.info("Запуск Gradio интерфейса...")

    # Запускаем веб-сервер Gradio.
    # server_name="0.0.0.0" делает приложение доступным для других устройств в той же сети.
    # server_port=7860 указывает порт, на котором будет работать приложение.
    try:
        interface.launch(server_name="0.0.0.0", server_port=7860, auth=(login, password), auth_message="Введите логин и пароль для доступа к приложению")
        # interface.launch(server_name="0.0.0.0", server_port=7860)
        logger.info("Gradio интерфейс успешно запущен.")
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске Gradio интерфейса: {e}", exc_info=True)
    finally:
        # Этот лог будет записан после остановки сервера (например, по Ctrl+C).
        logger.info("Gradio интерфейс остановлен.")
