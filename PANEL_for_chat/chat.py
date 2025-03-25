from typing import List
from hand_files import uploaded_files

chat_history = []

def chat_response(message: str, history: List[List[str]]) -> str:
    """Генерация ответа чата с учетом загруженных файлов"""
    history = history or []
    response = f"Вы сказали: {message}"
    
    # Добавляем информацию о файлах, если они есть
    if uploaded_files:
        file_list = "\n".join([f"- {name}" for name in uploaded_files.keys()])
        response += f"\n\nЗагруженные файлы:\n{file_list}"
    
    return response