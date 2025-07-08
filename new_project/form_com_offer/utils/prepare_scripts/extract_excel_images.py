#!/usr/bin/env python3
"""
Улучшенный скрипт для извлечения изображений из Excel файла.
Использует zipfile для доступа к встроенным медиафайлам.
"""

import os
import json
import zipfile
import shutil
from pathlib import Path
import pandas as pd
from PIL import Image

def extract_images_from_xlsx(excel_file_path, output_dir="docs/images_comp"):
    """
    Извлекает изображения из Excel файла используя zipfile.
    
    Args:
        excel_file_path (str): Путь к Excel файлу
        output_dir (str): Папка для сохранения изображений
        
    Returns:
        dict: Словарь с информацией об извлеченных изображениях
    """
    print(f"Извлечение изображений из файла: {excel_file_path}")
    
    if not os.path.exists(excel_file_path):
        print(f"Файл не найден: {excel_file_path}")
        return {}
    
    # Создаем папку для изображений
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    extracted_images = {}
    total_images = 0
    
    try:
        # Открываем Excel файл как ZIP архив
        with zipfile.ZipFile(excel_file_path, 'r') as zip_file:
            # Получаем список всех файлов в архиве
            file_list = zip_file.namelist()
            
            # Ищем медиафайлы
            media_files = [f for f in file_list if f.startswith('xl/media/')]
            
            if not media_files:
                print("В Excel файле не найдено изображений")
                return {}
            
            print(f"Найдено медиафайлов: {len(media_files)}")
            
            # Извлекаем каждое изображение
            for i, media_file in enumerate(media_files):
                try:
                    # Получаем расширение файла
                    file_ext = Path(media_file).suffix.lower()
                    if file_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                        continue
                    
                    # Читаем данные изображения
                    with zip_file.open(media_file) as img_file:
                        img_data = img_file.read()
                    
                    # Создаем PIL изображение для проверки
                    pil_img = Image.open(io.BytesIO(img_data))
                    
                    # Генерируем имя файла
                    image_name = f"component_image_{i + 1:03d}.jpg"
                    output_path = os.path.join(output_dir, image_name)
                    
                    # Сохраняем изображение в формате JPEG
                    if pil_img.mode in ('RGBA', 'LA', 'P'):
                        # Конвертируем в RGB для JPEG
                        pil_img = pil_img.convert('RGB')
                    
                    pil_img.save(output_path, 'JPEG', quality=90)
                    
                    # Сохраняем информацию об изображении
                    extracted_images[image_name] = {
                        'original_name': media_file,
                        'path': output_path,
                        'size': pil_img.size,
                        'format': pil_img.format,
                        'mode': pil_img.mode
                    }
                    
                    total_images += 1
                    print(f"  ✓ Сохранено: {image_name} (размер: {pil_img.size})")
                    
                except Exception as e:
                    print(f"  ✗ Ошибка при обработке {media_file}: {e}")
                    continue
            
            print(f"\nВсего извлечено изображений: {total_images}")
            
    except Exception as e:
        print(f"Ошибка при обработке Excel файла: {e}")
        return {}
    
    return extracted_images

def read_excel_data_for_matching(excel_file_path):
    """
    Читает данные из Excel файла для сопоставления с изображениями.
    
    Args:
        excel_file_path (str): Путь к Excel файлу
        
    Returns:
        dict: Данные из Excel файла
    """
    print(f"Чтение данных из Excel файла: {excel_file_path}")
    
    try:
        # Читаем все листы
        excel_data = pd.read_excel(excel_file_path, sheet_name=None)
        
        components_data = {}
        
        for sheet_name, df in excel_data.items():
            print(f"Обработка листа: {sheet_name}")
            
            # Фильтруем только строковые столбцы для поиска названий
            string_columns = [col for col in df.columns if isinstance(col, str)]
            print(f"Столбцы: {string_columns}")
            
            # Ищем столбцы с названиями компонентов
            name_columns = [col for col in string_columns if any(keyword in col.lower() 
                           for keyword in ['название', 'наименование', 'name', 'компонент', 'материал'])]
            
            if name_columns:
                print(f"  Найдены столбцы с названиями: {name_columns}")
                
                # Берем первые строки для анализа
                sample_data = df.head(50)  # Увеличиваем количество строк для анализа
                
                # Фильтруем пустые строки
                sample_data = sample_data.dropna(subset=name_columns, how='all')
                
                components_data[sheet_name] = {
                    'columns': string_columns,
                    'name_columns': name_columns,
                    'sample_data': sample_data.to_dict('records'),
                    'total_rows': len(df)
                }
                
                print(f"  Строк данных для анализа: {len(sample_data)}") 
            else:
                print(f"  Столбцы с названиями не найдены")
        
        return components_data
        
    except Exception as e:
        print(f"Ошибка при чтении Excel файла: {e}")
        return {}

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

def analyze_component_names(components_data, catalog):
    """
    Анализирует названия компонентов для сопоставления с изображениями.
    
    Args:
        components_data (dict): Данные из Excel файла
        catalog (dict): Каталог компонентов
        
    Returns:
        dict: Результат анализа
    """
    print("\nАнализ названий компонентов...")
    
    # Получаем названия компонентов из каталога
    catalog_names = set()
    if catalog and 'components' in catalog:
        for component in catalog['components']:
            catalog_names.add(component['name'].lower())
    
    print(f"Компонентов в каталоге: {len(catalog_names)}")
    
    # Анализируем данные из Excel
    excel_components = set()
    
    for sheet_name, sheet_data in components_data.items():
        print(f"\nАнализ листа: {sheet_name}")
        
        name_columns = sheet_data.get('name_columns', [])
        sample_data = sheet_data.get('sample_data', [])
        
        for row in sample_data:
            for col in name_columns:
                if col in row and row[col] and isinstance(row[col], str):
                    component_name = str(row[col]).strip().lower()
                    if component_name and len(component_name) > 3:  # Исключаем слишком короткие названия
                        excel_components.add(component_name)
    
    print(f"Уникальных компонентов в Excel: {len(excel_components)}")
    
    # Находим совпадения
    matches = catalog_names.intersection(excel_components)
    print(f"Совпадений: {len(matches)}")
    
    if matches:
        print("Найденные совпадения:")
        for match in sorted(matches):
            print(f"  - {match}")
    
    return {
        'catalog_names': catalog_names,
        'excel_components': excel_components,
        'matches': matches
    }

def create_images_folder(base_path="docs/images_comp"):
    """
    Создает папку для изображений компонентов.
    
    Args:
        base_path (str): Базовый путь для папки изображений
    """
    # Создаем базовую папку
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        print(f"Создана папка: {base_path}")
    else:
        print(f"Папка уже существует: {base_path}")

def main():
    """
    Основная функция.
    """
    print("=" * 60)
    print("Извлечение изображений комплектующих из Excel файла")
    print("=" * 60)
    
    # Путь к Excel файлу
    excel_file_path = "docs/prices_air_and_complectations/стоимости материалов кондиц.xlsx"
    
    # Проверяем существование файла
    if not os.path.exists(excel_file_path):
        print(f"Файл не найден: {excel_file_path}")
        return
    
    # Загружаем каталог компонентов
    catalog = load_components_catalog()
    if not catalog:
        print("Не удалось загрузить каталог компонентов!")
        return
    
    print(f"Загружен каталог с {len(catalog.get('components', []))} компонентами")
    
    # Создаем папку для изображений
    create_images_folder()
    
    # Читаем данные из Excel файла
    components_data = read_excel_data_for_matching(excel_file_path)
    
    if components_data:
        # Анализируем названия компонентов
        analysis = analyze_component_names(components_data, catalog)
        
        # Извлекаем изображения
        extracted_images = extract_images_from_xlsx(excel_file_path)
        
        if extracted_images:
            print(f"\n✓ Обработка завершена!")
            print(f"✓ Извлечено изображений: {len(extracted_images)}")
            print(f"✓ Найдено совпадений в названиях: {len(analysis.get('matches', []))}")
            
            # Сохраняем информацию об извлеченных изображениях
            output_file = "extracted_images_info.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'extracted_images': extracted_images,
                    'analysis': {
                        'catalog_names': list(analysis.get('catalog_names', [])),
                        'excel_components': list(analysis.get('excel_components', [])),
                        'matches': list(analysis.get('matches', []))
                    }
                }, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Информация сохранена в: {output_file}")
        else:
            print("\n⚠ Изображения не найдены!")
    else:
        print("\n⚠ Не удалось прочитать данные из Excel файла!")
    
    print("=" * 60)

if __name__ == "__main__":
    import io  # Добавляем импорт io
    main()
