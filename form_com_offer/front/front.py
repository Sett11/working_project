"""
Минимальный модуль фронтенда для поддержки new_front.py.
Содержит только необходимые функции и константы.
"""
import httpx
from utils.mylogger import Logger
import json
import os
import datetime

# Инициализация логгера
logger = Logger(name=__name__, log_file="frontend.log")

# Константы
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8001")
COMPONENTS_CATALOG_PATH = os.path.join(os.path.dirname(__file__), '../docs/components_catalog.json')
PLACEHOLDER_IMAGE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../docs/images_comp/placeholder.jpg'))

def load_components_catalog():
    """Загружает каталог комплектующих из JSON файла"""
    try:
        with open(COMPONENTS_CATALOG_PATH, encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Каталог компонентов успешно загружен: {len(data.get('components', []))} компонентов")
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки каталога комплектующих: {e}")
        return {"components": []}

# Глобальная переменная каталога
COMPONENTS_CATALOG = load_components_catalog()

def safe_float(value):
    """Безопасное преобразование в float"""
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def safe_int(value):
    """Безопасное преобразование в int"""
    if value is None or value == "":
        return 0
    try:
        return int(float(value))  # Сначала float, потом int для случаев типа "15.0"
    except (ValueError, TypeError):
        return 0

def safe_bool(value):
    """Безопасное преобразование в bool"""
    if value is None or value == "":
        return False
    try:
        return bool(value)
    except (ValueError, TypeError):
        return False

def get_component_image_path(image_path_from_json):
    """
    Получает абсолютный путь к изображению компонента по его относительному пути из JSON.
    """
    if not image_path_from_json:
        return PLACEHOLDER_IMAGE
    
    try:
        # Строим путь от корня проекта, где лежат папки docs, front и т.д.
        # Docker volume монтирует корень проекта в /app
        # Пример image_path_from_json: "images_comp/truba.jpg"
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        full_path = os.path.join(base_dir, 'docs', image_path_from_json)

        if os.path.exists(full_path):
            return full_path
        else:
            logger.warning(f"Файл изображения не найден по пути: {full_path}")
            return PLACEHOLDER_IMAGE
    except Exception as e:
        logger.error(f"Ошибка при получении изображения для {image_path_from_json}: {e}")
        return PLACEHOLDER_IMAGE

async def fetch_all_orders_list():
    """Получает объединенный список всех заказов"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/api/all_orders/")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Ошибка при получении объединенного списка заказов: {e}")
        return []

def get_placeholder_order():
    """Возвращает шаблон заказа с значениями по умолчанию"""
    return {
        "client_data": {
            "full_name": "Вася Плюшкин",
            "phone": "+375001111111",
            "email": "no_pain_no_gain@mail.ru",
            "address": "Минск, ул. ВесёлыхБобриков д. 89, корп. 1, кв. 99"
        },
        "order_params": {
            "room_area": 15,
            "room_type": "квартира",
            "discount": 5,
            "visit_date": datetime.date.today().strftime('%Y-%m-%d'),
            "installation_price": 666
        },
        "aircon_params": {
            "wifi": False,
            "inverter": False,
            "price_limit": 10000,
            "brand": "Любой",
            "mount_type": "Любой",
            "area": 15,
            "ceiling_height": 2.7,
            "illumination": "Средняя",
            "num_people": 1,
            "activity": "Сидячая работа",
            "num_computers": 0,
            "num_tvs": 0,
            "other_power": 0
        },
        "components": [
            {"name": comp.get("name", ""), "selected": False, "qty": 1, "length": 1} 
            for comp in COMPONENTS_CATALOG.get("components", [])
        ],
        "comment": "Оставьте комментарий..."
    }

def read_notes_md():
    """Заглушка для read_notes_md (файл notes.md удален)"""
    return "Инструкция временно недоступна."