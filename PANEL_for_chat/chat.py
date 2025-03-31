from typing import List
import requests
import asyncio
import aiohttp
from hand_files import get_formatted_documents_for_prompt
from logs import log_event
from config import know_client


def chat_response(message: str, history: List[List[str]]) -> str:
    return asyncio.run(async_chat_response(message, history))

async def async_chat_response(message: str, history: List[List[str]]) -> str:
    """Генерация ответа чата с учетом загруженных файлов"""
    try:
        log_event("CHAT_QUERY", f"Query: {message}")
        # Получаем содержимое документов для промпта
        documents_text = get_formatted_documents_for_prompt()
        # Если нет загруженных документов или они пустые
        if not documents_text or documents_text.strip() == "":
            log_event("CHAT_RESPONSE", "No documents available or documents are empty")
            return "Нет загруженных документов или документы пусты. Загрузите файлы для анализа."
        # Проверяем, что в документах есть реальный контент
        documents = documents_text.replace("<text_to_image>", "").replace("</text_to_image>", "").split("\n\n")
        valid_documents = [doc for doc in documents if doc.strip()]
        if not valid_documents:
            log_event("CHAT_RESPONSE", "All documents are empty or contain only markup")
            return "Ваши файлы или пустые или слишком большие."
        # Формируем промпт с документами
        system_prompt = f"""Ты — ассистент, который отвечает на вопросы на основе предоставленных документов. 
Используй в первую очередь информацию из документов и только после этого используй свою базу знаний. Если в документах нет никакой информации по вопросу, то дай краткий ответ с использованием своей базы знаний.
Ниже приведены документы в текстовом формате, на основе которых нужно отвечать. Если в документах изначально были изображения, то они будут помечены так: <text_to_image>описание изображения</text_to_image> и будут приведены в конце документа. Итак, документы:

{documents_text}

Отвечай на русском языке, структурированно и по делу."""
        log_event("CHAT_PROMPT", f"System prompt length: {len(system_prompt)}")
        log_event("CHAT_PROMPT", f"System prompt first 500 chars: {system_prompt[:500]}")
        # Используем Mistral API для генерации ответа
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
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{know_client['base_url']}/chat/completions", headers=headers, json=payload) as response:
                # Проверяем ответ
                if response.status == 200:
                    response_data = await response.json()
                else:
                    error_msg = f"Ошибка API: {response.status} - {response.text}"
                    log_event("ERROR", error_msg)
                    return f"Произошла ошибка при генерации ответа. Пожалуйста, попробуйте позже."
            answer = response_data["choices"][0]["message"]["content"]
            log_event("CHAT_RESPONSE", f"Generated response: {answer}")
            return answer
    except Exception as e:
        error_msg = f"Failed to generate chat response: {str(e)}"
        log_event("ERROR", error_msg)
        return f"Ошибка: {str(e)}"