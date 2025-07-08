#!/usr/bin/env python3
"""
Утилита для обновления и управления каталогом комплектующих.
"""

import json
import os
from datetime import datetime

def load_components_catalog(file_path="docs/JSON_files/components_catalog.json"):
    """
    Загружает каталог комплектующих из JSON файла.
    
    Args:
        file_path (str): Путь к JSON файлу каталога
        
    Returns:
        dict: Каталог комплектующих или None при ошибке
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Файл каталога не найден: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка при чтении JSON: {e}")
        return None

def save_components_catalog(catalog, file_path="docs/JSON_files/components_catalog.json"):
    """
    Сохраняет каталог комплектующих в JSON файл.
    
    Args:
        catalog (dict): Каталог комплектующих
        file_path (str): Путь к JSON файлу каталога
        
    Returns:
        bool: True при успешном сохранении, False при ошибке
    """
    try:
        # Создаем резервную копию
        backup_path = file_path + '.backup'
        if os.path.exists(file_path):
            import shutil
            shutil.copy2(file_path, backup_path)
        
        # Обновляем метаданные
        catalog['catalog_info']['updated_at'] = datetime.now().isoformat()
        catalog['catalog_info']['total_components'] = len(catalog['components'])
        
        # Сохраняем файл
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Ошибка при сохранении каталога: {e}")
        return False

def add_component(catalog, name, category, size, material, characteristics, price, standard=None, manufacturer=None):
    """
    Добавляет новый компонент в каталог.
    
    Args:
        catalog (dict): Каталог комплектующих
        name (str): Название компонента
        category (str): Категория компонента
        size (str): Размер компонента
        material (str): Материал компонента
        characteristics (str): Характеристики компонента
        price (float): Цена компонента
        standard (str, optional): Стандарт компонента
        manufacturer (str, optional): Производитель компонента
        
    Returns:
        bool: True при успешном добавлении, False при ошибке
    """
    try:
        # Проверяем, что компонент с таким именем еще не существует
        existing_names = [comp['name'] for comp in catalog['components']]
        if name in existing_names:
            print(f"Компонент '{name}' уже существует в каталоге!")
            return False
        
        # Создаем новый компонент
        new_id = max([comp['id'] for comp in catalog['components']], default=0) + 1
        
        new_component = {
            "id": new_id,
            "name": name,
            "category": category,
            "size": size,
            "material": material,
            "characteristics": characteristics,
            "price": price,
            "currency": "BYN",
            "standard": standard,
            "manufacturer": manufacturer,
            "in_stock": True,
            "description": f"{name}, размер: {size}, материал: {material}" + (f", характеристики: {characteristics}" if characteristics else ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Добавляем компонент в каталог
        catalog['components'].append(new_component)
        
        # Обновляем список категорий
        if category not in catalog['categories']:
            catalog['categories'].append(category)
            catalog['categories'].sort()
        
        print(f"✓ Компонент '{name}' успешно добавлен (ID: {new_id})")
        return True
        
    except Exception as e:
        print(f"Ошибка при добавлении компонента: {e}")
        return False

def update_component(catalog, component_id, **kwargs):
    """
    Обновляет существующий компонент в каталоге.
    
    Args:
        catalog (dict): Каталог комплектующих
        component_id (int): ID компонента для обновления
        **kwargs: Поля для обновления
        
    Returns:
        bool: True при успешном обновлении, False при ошибке
    """
    try:
        # Находим компонент по ID
        component = None
        for comp in catalog['components']:
            if comp['id'] == component_id:
                component = comp
                break
        
        if not component:
            print(f"Компонент с ID {component_id} не найден!")
            return False
        
        # Обновляем поля
        updatable_fields = ['name', 'category', 'size', 'material', 'characteristics', 
                           'price', 'standard', 'manufacturer', 'in_stock']
        
        for field, value in kwargs.items():
            if field in updatable_fields:
                component[field] = value
        
        # Обновляем описание
        if 'name' in kwargs or 'size' in kwargs or 'material' in kwargs or 'characteristics' in kwargs:
            component['description'] = f"{component['name']}, размер: {component['size']}, материал: {component['material']}" + (f", характеристики: {component['characteristics']}" if component['characteristics'] else "")
        
        # Обновляем время изменения
        component['updated_at'] = datetime.now().isoformat()
        
        # Обновляем список категорий
        if 'category' in kwargs:
            categories = list(set(comp['category'] for comp in catalog['components']))
            catalog['categories'] = sorted(categories)
        
        print(f"✓ Компонент с ID {component_id} успешно обновлен")
        return True
        
    except Exception as e:
        print(f"Ошибка при обновлении компонента: {e}")
        return False

def delete_component(catalog, component_id):
    """
    Удаляет компонент из каталога.
    
    Args:
        catalog (dict): Каталог комплектующих
        component_id (int): ID компонента для удаления
        
    Returns:
        bool: True при успешном удалении, False при ошибке
    """
    try:
        # Находим и удаляем компонент
        original_count = len(catalog['components'])
        catalog['components'] = [comp for comp in catalog['components'] if comp['id'] != component_id]
        
        if len(catalog['components']) == original_count:
            print(f"Компонент с ID {component_id} не найден!")
            return False
        
        # Обновляем список категорий
        categories = list(set(comp['category'] for comp in catalog['components']))
        catalog['categories'] = sorted(categories)
        
        print(f"✓ Компонент с ID {component_id} успешно удален")
        return True
        
    except Exception as e:
        print(f"Ошибка при удалении компонента: {e}")
        return False

def search_components(catalog, query, category=None):
    """
    Поиск компонентов в каталоге.
    
    Args:
        catalog (dict): Каталог комплектующих
        query (str): Поисковый запрос
        category (str, optional): Фильтр по категории
        
    Returns:
        list: Список найденных компонентов
    """
    results = []
    query_lower = query.lower()
    
    for component in catalog['components']:
        # Проверяем категорию
        if category and component['category'] != category:
            continue
        
        # Поиск по названию, описанию, размеру, материалу
        searchable_fields = [
            component['name'].lower(),
            component['description'].lower(),
            (component['size'] or '').lower(),
            (component['material'] or '').lower(),
            (component['characteristics'] or '').lower()
        ]
        
        if any(query_lower in field for field in searchable_fields):
            results.append(component)
    
    return results

def display_component_info(component):
    """
    Выводит информацию о компоненте.
    
    Args:
        component (dict): Компонент для отображения
    """
    print(f"ID: {component['id']}")
    print(f"Название: {component['name']}")
    print(f"Категория: {component['category']}")
    print(f"Размер: {component['size']}")
    print(f"Материал: {component['material']}")
    print(f"Характеристики: {component['characteristics']}")
    print(f"Цена: {component['price']} {component['currency']}")
    print(f"Стандарт: {component['standard']}")
    print(f"Производитель: {component['manufacturer']}")
    print(f"В наличии: {'Да' if component['in_stock'] else 'Нет'}")
    print(f"Описание: {component['description']}")
    print("-" * 50)

def main():
    """
    Основная функция для демонстрации работы утилиты.
    """
    print("=" * 60)
    print("Утилита управления каталогом комплектующих")
    print("=" * 60)
    
    # Загружаем каталог
    catalog = load_components_catalog()
    if not catalog:
        print("Не удалось загрузить каталог!")
        return
    
    print(f"Загружен каталог: {catalog['catalog_info']['name']}")
    print(f"Версия: {catalog['catalog_info']['version']}")
    print(f"Всего компонентов: {catalog['catalog_info']['total_components']}")
    print(f"Категорий: {len(catalog['categories'])}")
    
    # Пример поиска
    print("\n--- Поиск компонентов ---")
    results = search_components(catalog, "воздуховод")
    print(f"Найдено компонентов по запросу 'воздуховод': {len(results)}")
    
    # Выводим первые 3 результата
    for i, component in enumerate(results[:3], 1):
        print(f"\n{i}. {component['name']} - {component['price']} {component['currency']}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
