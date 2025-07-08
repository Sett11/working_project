#!/usr/bin/env python3
"""
Скрипт для создания заглушек изображений для компонентов каталога.
"""

import os
import json
from PIL import Image, ImageDraw, ImageFont
import textwrap

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

def create_placeholder_image(component, output_path, image_size=(400, 300)):
    """
    Создает заглушку изображения для компонента.
    
    Args:
        component (dict): Данные компонента
        output_path (str): Путь для сохранения изображения
        image_size (tuple): Размер изображения (ширина, высота)
    """
    try:
        # Создаем изображение
        img = Image.new('RGB', image_size, color='white')
        draw = ImageDraw.Draw(img)
        
        # Настройки цветов для разных категорий
        category_colors = {
            'Воздуховоды': '#4CAF50',
            'Отводы и повороты': '#2196F3',
            'Переходы': '#FF9800',
            'Тройники': '#9C27B0',
            'Врезки': '#F44336',
            'Насадки': '#00BCD4',
            'Клапаны': '#795548',
            'Оборудование': '#607D8B',
            'Материалы': '#8BC34A',
            'Соединительные элементы': '#FFE0B2',
            'Регулирующие элементы': '#E91E63',
            'Гибкие соединения': '#3F51B5'
        }
        
        # Выбираем цвет для категории
        category_color = category_colors.get(component['category'], '#757575')
        
        # Создаем градиент
        for i in range(image_size[1]):
            opacity = int(255 * (1 - i / image_size[1] * 0.3))
            color = tuple(int(category_color[j:j+2], 16) for j in (1, 3, 5))
            gradient_color = tuple(min(255, max(0, c + opacity - 255)) for c in color)
            draw.line([(0, i), (image_size[0], i)], fill=gradient_color)
        
        # Рисуем рамку
        draw.rectangle([0, 0, image_size[0]-1, image_size[1]-1], outline='#CCCCCC', width=2)
        
        # Добавляем текст
        try:
            # Пытаемся использовать системный шрифт
            font_large = ImageFont.truetype("arial.ttf", 18)
            font_medium = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            # Fallback на стандартный шрифт
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Заголовок
        title = component['name']
        if len(title) > 30:
            title = title[:30] + "..."
        
        # Позиционируем текст
        y_offset = 20
        
        # Название компонента
        text_bbox = draw.textbbox((0, 0), title, font=font_large)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (image_size[0] - text_width) // 2
        draw.text((text_x, y_offset), title, fill='white', font=font_large)
        y_offset += 30
        
        # Категория
        category_text = f"Категория: {component['category']}"
        text_bbox = draw.textbbox((0, 0), category_text, font=font_medium)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (image_size[0] - text_width) // 2
        draw.text((text_x, y_offset), category_text, fill='white', font=font_medium)
        y_offset += 25
        
        # Размер
        if component['size']:
            size_text = f"Размер: {component['size']}"
            text_bbox = draw.textbbox((0, 0), size_text, font=font_medium)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (image_size[0] - text_width) // 2
            draw.text((text_x, y_offset), size_text, fill='white', font=font_medium)
            y_offset += 25
        
        # Материал
        if component['material']:
            material_text = f"Материал: {component['material']}"
            text_bbox = draw.textbbox((0, 0), material_text, font=font_small)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (image_size[0] - text_width) // 2
            draw.text((text_x, y_offset), material_text, fill='white', font=font_small)
            y_offset += 20
        
        # Цена
        price_text = f"Цена: {component['price']} {component['currency']}"
        text_bbox = draw.textbbox((0, 0), price_text, font=font_medium)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (image_size[0] - text_width) // 2
        draw.text((text_x, image_size[1] - 40), price_text, fill='white', font=font_medium)
        
        # Добавляем водяной знак
        watermark = "ОБРАЗЕЦ"
        text_bbox = draw.textbbox((0, 0), watermark, font=font_small)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = image_size[0] - text_width - 10
        draw.text((text_x, 10), watermark, fill=(255, 255, 255, 128), font=font_small)
        
        # Сохраняем изображение
        img.save(output_path, 'JPEG', quality=85)
        return True
        
    except Exception as e:
        print(f"Ошибка при создании изображения для {component['name']}: {e}")
        return False

def create_category_folders(base_path="images_comp"):
    """
    Создает папки для категорий компонентов.
    
    Args:
        base_path (str): Базовый путь для папок изображений
    """
    categories = [
        "воздуховоды", "отводы_повороты", "переходы", "тройники", 
        "врезки", "насадки", "клапаны", "оборудование", "материалы",
        "соединительные_элементы", "регулирующие_элементы", "гибкие_соединения"
    ]
    
    # Создаем базовую папку
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    # Создаем папки для категорий
    for category in categories:
        category_path = os.path.join(base_path, category)
        if not os.path.exists(category_path):
            os.makedirs(category_path)
            print(f"Создана папка: {category_path}")

def create_all_component_images():
    """
    Создает заглушки изображений для всех компонентов.
    """
    print("=" * 60)
    print("Создание заглушек изображений для компонентов")
    print("=" * 60)
    
    # Загружаем каталог
    catalog = load_components_catalog()
    if not catalog:
        print("Не удалось загрузить каталог!")
        return False
    
    # Создаем папки для категорий
    create_category_folders()
    
    # Счетчики
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"Обработка {len(catalog['components'])} компонентов...")
    
    for component in catalog['components']:
        # Формируем путь к изображению
        image_path = os.path.join("images_comp", component['image_path'])
        
        # Проверяем, существует ли уже изображение
        if os.path.exists(image_path):
            print(f"Пропущен {component['name']} - файл уже существует")
            skipped_count += 1
            continue
        
        # Создаем изображение
        success = create_placeholder_image(component, image_path)
        
        if success:
            print(f"✓ Создано изображение для: {component['name']}")
            created_count += 1
        else:
            print(f"✗ Ошибка при создании изображения для: {component['name']}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print("Результаты создания изображений:")
    print(f"✓ Создано: {created_count}")
    print(f"⚠ Пропущено: {skipped_count}")
    print(f"✗ Ошибок: {error_count}")
    print("=" * 60)
    
    return error_count == 0

def main():
    """
    Основная функция.
    """
    success = create_all_component_images()
    
    if success:
        print("\n✓ Все изображения созданы успешно!")
    else:
        print("\n⚠ Создание изображений завершено с ошибками!")

if __name__ == "__main__":
    main()
