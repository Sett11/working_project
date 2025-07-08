#!/usr/bin/env python3
"""
Скрипт для создания JSON-файла с комплектующими для систем вентиляции и кондиционирования.
"""

import json
import os
from datetime import datetime

# Импортируем данные из файла с компонентами
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Структура данных компонентов
components_data = {
    # Воздуховоды прямоугольные
    "воздуховод 500х800": ("500x800 мм", "оцинкованная сталь", "класс герметичности А", 5000, "ГОСТ 14918-80"),
    "воздуховод 600х300": ("600x300 мм", "оцинкованная сталь", "класс герметичности А", 3500, "ГОСТ 14918-80"),
    "воздуховод 800х500": ("800x500 мм", "оцинкованная сталь", "класс герметичности А", 4500, "ГОСТ 14918-80"),
    
    # Воздуховоды круглые
    "воздуховод d450": ("ø450 мм", "оцинкованная сталь", "класс герметичности А", 2500, "ГОСТ 14918-80"),
    "воздуховод d560": ("ø560 мм", "оцинкованная сталь", "класс герметичности А", 3000, "ГОСТ 14918-80"),
    "воздуховод d630": ("ø630 мм", "оцинкованная сталь", "класс герметичности А", 3500, "ГОСТ 14918-80"),
    "воздуховод d710": ("ø710 мм", "оцинкованная сталь", "класс герметичности А", 4000, "ГОСТ 14918-80"),

    # Фасонные части (отводы)
    "поворот 90° 500х800": ("500x800 мм", "оцинкованная сталь", "угол 90°", 1200, None),
    "поворот 90° d630": ("ø630 мм", "оцинкованная сталь", "угол 90°", 900, None),
    "поворот 90° d560": ("ø560 мм", "оцинкованная сталь", "угол 90°", 850, None),
    "поворот 90° d450": ("ø450 мм", "оцинкованная сталь", "угол 90°", 800, None),
    "поворот 90° d710": ("ø710 мм", "оцинкованная сталь", "угол 90°", 1100, None),

    # Переходы
    "переход 500х800/d630": ("500x800 → ø630 мм", "оцинкованная сталь", None, 1500, None),
    "переход 600х300/d560": ("600x300 → ø560 мм", "оцинкованная сталь", None, 1400, None),
    "переход 500х800/d450": ("500x800 → ø450 мм", "оцинкованная сталь", None, 1300, None),

    # Тройники
    "тройник 500х800/800х500/500х800": ("500x800/800x500/500x800 мм", "оцинкованная сталь", None, 2000, None),

    # Врезки
    "врезка в воздуховод d710": ("для ø710 мм", "оцинкованная сталь", None, 800, None),

    # Насадки с водоотводящим кольцом
    "Насадок с водоотводящим кольцом НВК-560-Р-ОЦ": ("ø560 мм", "оцинкованная сталь", "водоотводящее кольцо", 21.8, "НЕВАТОМ"),
    "Насадок с водоотводящим кольцом НВК-630-Р-ОЦ": ("ø630 мм", "оцинкованная сталь", "водоотводящее кольцо", 22.4, "НЕВАТОМ"),
    "Насадок с водоотводящим кольцом НВК-710-Р-ОЦ": ("ø710 мм", "оцинкованная сталь", "водоотводящее кольцо", 30.0, "НЕВАТОМ"),

    # Клапаны
    "Клапан воздушный регулирующий РЕГУЛЯР-Л-800х500-В-1": ("800x500 мм", "взрывозащищенное исполнение", "ручной привод", 12000, "ВЕЗА"),
    "Клапан воздушный регулирующий РЕГУЛЯР-600*300-Н-1": ("600x300 мм", None, "ручной привод", 9000, "ВЕЗА"),
    "Клапан воздушный регулирующий РЕГУЛЯР-Л-450-Н-1": ("ø450 мм", None, "ручной привод", 9.2, "ВЕЗА"),

    # Оборудование
    "Фильтровентиляционный агрегат AirTech P30": ("30000 м3/ч", "22 кВт", "шумопоглощающий корпус", 150000, "TEKA"),
    "Фильтровентиляционная установка FCS-6000-06": ("6000 м3/ч", None, None, 80000, None),

    # Материалы
    "тонколистовая оц. Сталь б=0,5мм": ("0.5 мм", "оцинкованная сталь", "для окожушивания", 500, None),
    "Маты минераловатные Акотерм СТИ 50/А": ("40 мм", "с покровным слоем из фольги", "теплоизоляция", 300, None),

    # Дополнительные комплектующие
    "Отвод 90° круглый": ("ø100-1250 мм", "оцинкованная сталь", "угол 90°", 400, None),
    "Отвод 60° круглый": ("ø100-1250 мм", "оцинкованная сталь", "угол 60°", 350, None),
    "Отвод 45° круглый": ("ø100-1250 мм", "оцинкованная сталь", "угол 45°", 300, None),
    "Отвод 30° круглый": ("ø100-1250 мм", "оцинкованная сталь", "угол 30°", 250, None),
    "Ниппель": ("ø100-1250 мм", "оцинкованная сталь", "для соединения воздуховодов", 200, None),
    "Муфта": ("ø100-1250 мм", "оцинкованная сталь", "для соединения воздуховодов", 220, None),
    "Заглушка круглая": ("ø100-1250 мм", "оцинкованная сталь", "защитная функция", 150, None),
    "Дроссель-клапан": ("ø100-500 мм", "оцинкованная сталь", "регулирование воздуха", 600, None),
    "Зонт крышный": ("ø100-710 мм", "оцинкованная сталь", "защита от осадков", 450, None),
    "Дефлектор": ("ø200-1250 мм", "оцинкованная сталь", "увеличение тяги", 700, None),
    "Гибкие вставки": ("ø102-508 мм", "оцинкованная сталь", "виброгашение", 350, None)
}

def convert_to_json_format(components_data):
    """
    Конвертирует данные компонентов в формат JSON.
    
    Args:
        components_data (dict): Исходные данные компонентов
        
    Returns:
        list: Список компонентов в формате JSON
    """
    components_list = []
    
    for component_name, (size, material, characteristics, price, standard) in components_data.items():
        # Определяем категорию компонента (для папки)
        category_folder = determine_category(component_name)
        
        # Получаем отображаемое название категории
        category_display = get_category_display_name(category_folder)
        
        # Генерируем путь к изображению (все изображения в корне папки)
        image_path = f"{component_name}.jpg"
        
        # Создаем объект компонента
        component = {
            "id": len(components_list) + 1,
            "name": component_name,
            "category": category_display,
            "category_folder": category_folder,
            "size": size,
            "material": material,
            "characteristics": characteristics,
            "price": price,
            "currency": "BYN",
            "standard": standard,
            "manufacturer": standard if standard and standard != "ГОСТ 14918-80" else None,
            "in_stock": True,
            "description": generate_description(component_name, size, material, characteristics),
            "image_path": image_path,
            "image_url": f"./docs/images_comp/{image_path}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        components_list.append(component)
    
    return components_list

# Helper function to generate image paths
def generate_image_path(component_name, category):
    return f"{category}/{component_name}.jpg"

def determine_category(component_name):
    """
    Определяет категорию компонента на основе его названия.
    
    Args:
        component_name (str): Название компонента
        
    Returns:
        str: Категория компонента
    """
    name_lower = component_name.lower()
    
    if "воздуховод" in name_lower:
        return "воздуховоды"
    elif "поворот" in name_lower or "отвод" in name_lower:
        return "отводы_повороты"
    elif "переход" in name_lower:
        return "переходы"
    elif "тройник" in name_lower:
        return "тройники"
    elif "врезка" in name_lower:
        return "врезки"
    elif "насадок" in name_lower:
        return "насадки"
    elif "клапан" in name_lower:
        return "клапаны"
    elif "агрегат" in name_lower or "установка" in name_lower:
        return "оборудование"
    elif "сталь" in name_lower or "мат" in name_lower:
        return "материалы"
    elif "ниппель" in name_lower or "муфта" in name_lower or "заглушка" in name_lower:
        return "соединительные_элементы"
    elif "дроссель" in name_lower or "зонт" in name_lower or "дефлектор" in name_lower:
        return "регулирующие_элементы"
    elif "гибкие" in name_lower:
        return "гибкие_соединения"
    else:
        return "прочие_комплектующие"

def get_category_display_name(folder_name):
    """
    Преобразует название папки в отображаемое название категории.
    
    Args:
        folder_name (str): Название папки
        
    Returns:
        str: Отображаемое название категории
    """
    category_map = {
        "воздуховоды": "Воздуховоды",
        "отводы_повороты": "Отводы и повороты",
        "переходы": "Переходы",
        "тройники": "Тройники",
        "врезки": "Врезки",
        "насадки": "Насадки",
        "клапаны": "Клапаны",
        "оборудование": "Оборудование",
        "материалы": "Материалы",
        "соединительные_элементы": "Соединительные элементы",
        "регулирующие_элементы": "Регулирующие элементы",
        "гибкие_соединения": "Гибкие соединения",
        "прочие_комплектующие": "Прочие комплектующие"
    }
    return category_map.get(folder_name, folder_name)

def generate_description(name, size, material, characteristics):
    """
    Генерирует описание компонента.
    
    Args:
        name (str): Название компонента
        size (str): Размер
        material (str): Материал
        characteristics (str): Характеристики
        
    Returns:
        str: Описание компонента
    """
    description_parts = [f"{name}"]
    
    if size:
        description_parts.append(f"размер: {size}")
    
    if material:
        description_parts.append(f"материал: {material}")
    
    if characteristics:
        description_parts.append(f"характеристики: {characteristics}")
    
    return ", ".join(description_parts)

def create_components_json():
    """
    Создает JSON-файл с комплектующими.
    """
    print("=" * 60)
    print("Создание JSON-файла с комплектующими")
    print("=" * 60)
    
    # Конвертируем данные в JSON формат
    components_list = convert_to_json_format(components_data)
    
    # Создаем структуру каталога
    catalog_structure = {
        "catalog_info": {
            "name": "Каталог комплектующих для систем вентиляции и кондиционирования",
            "description": "Полный каталог комплектующих для монтажа систем вентиляции и кондиционирования",
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "total_components": len(components_list),
            "currency": "BYN"
        },
        "categories": list(set(component["category"] for component in components_list)),
        "components": components_list
    }
    
    # Создаем папку для JSON файлов если её нет
    output_dir = "docs/JSON_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Сохраняем JSON файл
    output_file = os.path.join(output_dir, "components_catalog.json")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(catalog_structure, f, ensure_ascii=False, indent=2)
        
        print(f"✓ JSON-файл создан: {output_file}")
        print(f"✓ Всего компонентов: {len(components_list)}")
        print(f"✓ Категорий: {len(catalog_structure['categories'])}")
        print("\nКатегории:")
        for category in sorted(catalog_structure['categories']):
            count = sum(1 for comp in components_list if comp['category'] == category)
            print(f"  - {category}: {count} компонентов")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка при создании файла: {e}")
        return False

def main():
    """
    Основная функция.
    """
    success = create_components_json()
    
    if success:
        print("\n✓ Скрипт завершён успешно!")
    else:
        print("\n✗ Скрипт завершён с ошибкой!")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
