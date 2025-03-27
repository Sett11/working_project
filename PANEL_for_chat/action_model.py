import os
import requests
import io
import base64
from typing import Optional, Dict, Any, List
from PIL import Image
from logs import log_event
from config import know_client

def prepare_image_for_api(image: Image.Image) -> str:
    """Подготовка изображения для отправки в API"""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return base64.b64encode(img_byte_arr.read()).decode('utf-8')

def create_image_prompt() -> str:
    """Создание промпта для анализа изображения"""
    return "Опиши подробно содержание этого изображения. Если это график, таблица или другая визуализация данных, опиши все представленные данные. Если это текст, приведи его дословно."

def create_image_message(img_base64: str) -> List[Dict[str, Any]]:
    """Создание сообщения с изображением для API"""
    return [
        {
            "type": "text",
            "text": create_image_prompt()
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_base64}"
            }
        }
    ]

def create_api_payload(messages: List[Dict[str, Any]], temperature: float = 0.2) -> Dict[str, Any]:
    """Создание payload для API запроса"""
    return {
        "model": know_client['model'],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": know_client['max_tokens']
    }

def describe_image(image: Image.Image) -> Optional[str]:
    """
    Отправляет изображение на анализ через Mistral API и получает текстовое описание.
    
    Args:
        image: PIL изображение для анализа
        
    Returns:
        str: Текстовое описание изображения или None в случае ошибки
    """
    try:
        # Подготавливаем изображение
        img_base64 = prepare_image_for_api(image)
        
        # Формируем запрос к API
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {know_client['api_key']}"
        }
        
        # Создаем сообщение и payload
        messages = [{"role": "user", "content": create_image_message(img_base64)}]
        payload = create_api_payload(messages)
        
        # Отправляем запрос
        response = requests.post(f"{know_client['base_url']}/chat/completions", headers=headers, json=payload)
        
        # Проверяем ответ
        if response.status_code == 200:
            response_data = response.json()
            description = response_data["choices"][0]["message"]["content"]
            log_event("IMAGE_ANALYSIS", "Successfully described image")
            return description
        else:
            log_event("ERROR", f"Failed API call to Mistral API: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        log_event("ERROR", f"Failed to describe image: {str(e)}")
        return None

def fallback_describe_image_openai(image: Image.Image) -> Optional[str]:
    """
    Запасной метод описания изображения через OpenAI API, если Mistral недоступен
    
    Args:
        image: PIL изображение для анализа
        
    Returns:
        str: Текстовое описание изображения или None в случае ошибки
    """
    try:
        from openai import OpenAI
        
        # Получаем ключ API из переменной окружения
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            log_event("ERROR", "OpenAI API key is not set")
            return None
            
        client = OpenAI(api_key=api_key)
        
        # Подготавливаем изображение и создаем сообщение
        img_base64 = prepare_image_for_api(image)
        messages = [{"role": "user", "content": create_image_message(img_base64)}]
        
        # Отправляем запрос к OpenAI API
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=know_client['max_tokens']
        )
        
        description = response.choices[0].message.content
        log_event("IMAGE_ANALYSIS", "Successfully described image using OpenAI")
        return description
        
    except Exception as e:
        log_event("ERROR", f"Failed to describe image with OpenAI: {str(e)}")
        return None