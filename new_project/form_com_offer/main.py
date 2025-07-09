from front.front import interface, logger

# Основная точка входа в приложение фронтенда.
# Мы импортируем готовый интерфейс из front.py и запускаем его.

if __name__ == "__main__":
    logger.info("Запуск Gradio интерфейса...")
    
    # Запускаем сервер Gradio, чтобы он был доступен извне контейнера.
    # Убрана аутентификация для простоты на время разработки.
    interface.launch(server_name="0.0.0.0", server_port=7860)
    
    logger.info("Gradio интерфейс остановлен.")