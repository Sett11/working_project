import aiohttp
import io
import base64
import asyncio
from typing import Optional, Dict, Any, List
from PIL import Image
import asyncio
from logs import log_event
from config import know_client

def prepare_image_for_api(image: Image.Image) -> str:
    """Подготовка изображения для отправки в API"""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return base64.b64encode(img_byte_arr.read()).decode('utf-8')

def create_image_message(img_base64: str) -> List[Dict[str, Any]]:
    """Создание сообщения с изображением для API"""
    return [
        {
            "type": "text",
            "text": "Если представленное тебе изображение является графиком, информационным графиком, таблицей или другой визуализацией данных - предоставь подробное описание этого изображения. В противном случае верни пустую строку."
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
    

async def describe_image(image: Image.Image) -> Optional[str]:
    """
    Отправляет изображение на анализ через Mistral API и получает текстовое описание.
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
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{know_client['base_url']}/chat/completions", headers=headers, json=payload) as response:
                # Проверяем ответ
                if response.status == 200:
                    response_data = await response.json()
                    description = response_data["choices"][0]["message"]["content"]
                    log_event("IMAGE_ANALYSIS", "Successfully described image")
                    return description
                else:
                    log_event("ERROR", f"Failed API call to Mistral API: {response.status} - {response.text}")
                    return ''
    except Exception as e:
        log_event("ERROR", f"Failed to describe image: {str(e)}")
        return ''
    
async def describe_images(images: List[Image.Image]) -> List[Optional[str]]:
    """
    Асинхронно анализирует список изображений и возвращает список их описаний.
    """
    return await asyncio.gather(*(describe_image(image) for image in images))

def describe_images_sync(images: List[Image.Image]) -> List[Optional[str]]:
    """
    Синхронно анализирует список изображений и возвращает список их описаний.
    """
    return asyncio.run(describe_images(images))


