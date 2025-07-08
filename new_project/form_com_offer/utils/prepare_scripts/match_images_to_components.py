#!/usr/bin/env python3
"""
Скрипт для сопоставления извлеченных изображений с компонентами в JSON файле.
"""

import os
import json
import shutil
from datetime import datetime

def load_components_catalog(file_path="docs/JSON_files/components_catalog.json"):
    """
    Загружает каталог компонентов из JSON файла.
    
    Args:
        file_path (str): Путь к JSON файлу каталога
        
    Returns:
        dict: Каталог компонентов или None при ошибке
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

def load_extracted_images_info(file_path="extracted_images_info.json"):
    """
    Загружает информацию об извлеченных изображениях.
    
    Args:
        file_path (str): Путь к JSON файлу с информацией об изображениях
        
    Returns:
        dict: Информация об изображениях или None при ошибке
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Файл с информацией об изображениях не найден: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка при чтении JSON: {e}")
        return None

def get_available_images(images_dir="docs/images_comp"):
    """
    Получает список доступных изображений в папке.
    
    Args:
        images_dir (str): Путь к папке с изображениями
        
    Returns:
        list: Список имен файлов изображений
    """
    if not os.path.exists(images_dir):
        print(f"Папка с изображениями не найдена: {images_dir}")
        return []
    
    image_files = []
    for filename in os.listdir(images_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            image_files.append(filename)
    
    return sorted(image_files)

def match_components_to_images(catalog, available_images):
    """
    Сопоставляет компоненты с доступными изображениями.
    
    Args:
        catalog (dict): Каталог компонентов
        available_images (list): Список доступных изображений
        
    Returns:
        dict: Результат сопоставления
    """
    print("Сопоставление компонентов с изображениями...")
    
    if not catalog or 'components' not in catalog:
        print("Каталог компонентов пуст или некорректен")
        return {}
    
    components = catalog['components']
    total_components = len(components)
    total_images = len(available_images)
    
    print(f"Компонентов в каталоге: {total_components}")
    print(f"Доступных изображений: {total_images}")
    
    # Простое сопоставление по порядку
    matched_components = []
    
    for i, component in enumerate(components):
        # Берем изображение по порядку, если оно есть
        if i < len(available_images):
            image_filename = available_images[i]
            
            # Обновляем информацию о компоненте
            updated_component = component.copy()
            updated_component['image_path'] = image_filename
            updated_component['image_url'] = f"./docs/images_comp/{image_filename}"
            updated_component['updated_at'] = datetime.now().isoformat()
            updated_component['has_image'] = True
            
            matched_components.append(updated_component)
            print(f"  ✓ {component['name']} → {image_filename}")
        else:
            # Компонент без изображения
            updated_component = component.copy()
            updated_component['image_path'] = None
            updated_component['image_url'] = None
            updated_component['updated_at'] = datetime.now().isoformat()
            updated_component['has_image'] = False
            
            matched_components.append(updated_component)
            print(f"  ✗ {component['name']} → БЕЗ ИЗОБРАЖЕНИЯ")
    
    return {
        'components': matched_components,
        'total_components': total_components,
        'total_images': total_images,
        'matched_count': min(total_components, total_images),
        'unmatched_components': max(0, total_components - total_images),
        'unused_images': max(0, total_images - total_components)
    }

def update_catalog_with_images(catalog, matching_result):
    """
    Обновляет каталог компонентов с привязанными изображениями.
    
    Args:
        catalog (dict): Исходный каталог компонентов
        matching_result (dict): Результат сопоставления
        
    Returns:
        dict: Обновленный каталог
    """
    updated_catalog = catalog.copy()
    updated_catalog['components'] = matching_result['components']
    updated_catalog['catalog_info']['updated_at'] = datetime.now().isoformat()
    updated_catalog['catalog_info']['total_components'] = matching_result['total_components']
    updated_catalog['catalog_info']['images_matched'] = matching_result['matched_count']
    
    return updated_catalog

def save_updated_catalog(catalog, file_path="docs/JSON_files/components_catalog.json"):
    """
    Сохраняет обновленный каталог компонентов.
    
    Args:
        catalog (dict): Обновленный каталог
        file_path (str): Путь для сохранения файла
        
    Returns:
        bool: True если сохранение прошло успешно
    """
    try:
        # Создаем резервную копию
        backup_path = file_path + ".backup"
        if os.path.exists(file_path):
            shutil.copy2(file_path, backup_path)
            print(f"Создана резервная копия: {backup_path}")
        
        # Сохраняем обновленный каталог
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Обновленный каталог сохранен: {file_path}")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка при сохранении каталога: {e}")
        return False

def main():
    """
    Основная функция.
    """
    print("=" * 60)
    print("Сопоставление изображений с компонентами")
    print("=" * 60)
    
    # Загружаем каталог компонентов
    catalog = load_components_catalog()
    if not catalog:
        print("Не удалось загрузить каталог компонентов!")
        return
    
    print(f"Загружен каталог с {len(catalog.get('components', []))} компонентами")
    
    # Получаем список доступных изображений
    available_images = get_available_images()
    if not available_images:
        print("Не найдено доступных изображений!")
        return
    
    print(f"Найдено изображений: {len(available_images)}")
    
    # Выводим список изображений
    print("\nДоступные изображения:")
    for i, image in enumerate(available_images, 1):
        print(f"  {i:2d}. {image}")
    
    # Сопоставляем компоненты с изображениями
    matching_result = match_components_to_images(catalog, available_images)
    
    if matching_result:
        print(f"\n✓ Результат сопоставления:")
        print(f"  - Всего компонентов: {matching_result['total_components']}")
        print(f"  - Всего изображений: {matching_result['total_images']}")
        print(f"  - Сопоставлено: {matching_result['matched_count']}")
        print(f"  - Компонентов без изображений: {matching_result['unmatched_components']}")
        print(f"  - Неиспользованных изображений: {matching_result['unused_images']}")
        
        # Обновляем каталог
        updated_catalog = update_catalog_with_images(catalog, matching_result)
        
        # Сохраняем обновленный каталог
        if save_updated_catalog(updated_catalog):
            print("\n✓ Каталог успешно обновлен!")
        else:
            print("\n✗ Ошибка при сохранении каталога!")
    else:
        print("\n✗ Ошибка при сопоставлении!")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
