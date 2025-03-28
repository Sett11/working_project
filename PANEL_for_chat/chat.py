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
        
        # Если нет загруженных документов или они пустые
        if not documents_text or documents_text.strip() == "":
            log_event("CHAT_RESPONSE", "No documents available or documents are empty")
            return "Нет загруженных документов или документы пусты. Загрузите файлы для анализа."
        
        # Проверяем, что в документах есть реальный контент
        documents = documents_text.split("\n\n")
        valid_documents = [doc for doc in documents if doc.strip() and not doc.startswith("<") or not doc.endswith(">")]
        
        if not valid_documents:
            log_event("CHAT_RESPONSE", "All documents are empty or contain only markup")
            return "Ваши файлы или пустые или слишком большие."
        
        # Формируем промпт с документами
        system_prompt = f"""Ты — ассистент, который отвечает на вопросы на основе предоставленных документов. 
Используй в первую очередь информацию из документов и только после этого используй свою базу знаний. Если в документах нет никакой информации по вопросу, то дай краткий ответ с использованием своей базы знаний.
Ниже приведены документы, на основе которых нужно отвечать:

{documents_text}

Отвечай на русском языке, структурированно и по делу."""
        
        log_event("CHAT_PROMPT", f"System prompt length: {len(system_prompt)}")
        log_event("CHAT_PROMPT", f"System prompt first 500 chars: {system_prompt[:500]}")
        
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
        
        log_event("CHAT_REQUEST", f"Request payload: {str(payload)}")
        
        # Отправляем запрос
        response = requests.post(f"{know_client['base_url']}/chat/completions", headers=headers, json=payload)
        
        # Проверяем ответ
        if response.status_code == 200:
            response_data = response.json()
            answer = response_data["choices"][0]["message"]["content"]
            log_event("CHAT_RESPONSE", f"Generated response: {answer}")
            return answer
        else:
            error_msg = f"Ошибка API: {response.status_code} - {response.text}"
            log_event("ERROR", error_msg)
            return f"Произошла ошибка при генерации ответа. Пожалуйста, попробуйте позже."
            
    except Exception as e:
        error_msg = f"Failed to generate chat response: {str(e)}"
        log_event("ERROR", error_msg)
        return f"Ошибка: {str(e)}"