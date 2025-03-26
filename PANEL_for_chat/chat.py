from typing import List
from hand_files import get_documents_for_prompt
from logs import log_event
from config import know_client

chat_history = []

def chat_response(message: str, history: List[List[str]]) -> str:
    """Генерация ответа чата с учетом загруженных файлов"""
    try:
        history = history or []
        log_event("CHAT_QUERY", f"Query: {message}")
        
        # Получаем содержимое документов для промпта
        documents_text = get_documents_for_prompt()
        
        # Если нет загруженных документов
        if not documents_text:
            log_event("CHAT_RESPONSE", "No documents available")
            return "Нет загруженных документов. Загрузите файлы для анализа."
        
        # Формируем промпт с документами
        system_prompt = """Ты — ассистент, который отвечает на вопросы на основе предоставленных документов. 
Используй только информацию из документов. Если в документах нет ответа, скажи, что не можешь ответить.
Ниже приведены документы, на основе которых нужно отвечать:

{documents}

Отвечай на русском языке, структурированно и по делу."""
        
        system_prompt = system_prompt.format(documents=documents_text)
        
        # Используем Mistral API для генерации ответа
        import requests
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {know_client['api_key']}"
        }
        
        # Создаем промпт для модели
        payload = {
            "model": know_client['model'],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "temperature": 0.3,
            "max_tokens": know_client['max_tokens']
        }
        
        # Добавляем историю чата, если она есть
        if history:
            for h in history:
                if len(h) == 2:  # Проверяем, что в истории есть пары [вопрос, ответ]
                    payload["messages"].insert(1, {"role": "user", "content": h[0]})
                    payload["messages"].insert(2, {"role": "assistant", "content": h[1]})
        
        # Отправляем запрос
        response = requests.post(f"{know_client['base_url']}/chat/completions", headers=headers, json=payload)
        
        # Проверяем ответ
        if response.status_code == 200:
            response_data = response.json()
            answer = response_data["choices"][0]["message"]["content"]
            log_event("CHAT_RESPONSE", "Successfully generated response")
            return answer
        else:
            error_msg = f"Ошибка API: {response.status_code} - {response.text}"
            log_event("ERROR", error_msg)
            return f"Произошла ошибка при генерации ответа. Пожалуйста, попробуйте позже."
            
    except Exception as e:
        error_msg = f"Failed to generate chat response: {str(e)}"
        log_event("ERROR", error_msg)
        return f"Ошибка: {str(e)}"

# Создать config.py
class Config:
    MAX_CHARS = 100000
    MAX_FILE_SIZE = 10 * 1024 * 1024
    UPLOADS_DIR = "uploads"
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.pptx'}
    MAX_HISTORY_LENGTH = 5