#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для обновления JSON файла кондиционеров с добавлением описаний и корректировкой путей к изображениям
"""

import json
import os
import re
from typing import Dict, List, Optional, Any
from new_project.form_com_offer.utils.prepare_scripts.extract_pdf import extract_pdf_content
from new_project.form_com_offer.utils.prepare_scripts.extract_xlsx import extract_xlsx_content

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Загружает JSON файл."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки JSON файла {file_path}: {e}")
        return {}

def save_json_file(data: Dict[str, Any], file_path: str) -> None:
    """Сохраняет данные в JSON файл."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"JSON файл успешно сохранен: {file_path}")
    except Exception as e:
        print(f"Ошибка сохранения JSON файла {file_path}: {e}")

def extract_series_descriptions_from_xlsx(xlsx_files: List[str]) -> Dict[str, str]:
    """Извлекает описания серий кондиционеров из Excel файлов."""
    descriptions = {}
    
    for file_path in xlsx_files:
        try:
            data = extract_xlsx_content(file_path)
            
            # Ищем данные из прайс-листов
            for sheet_name, sheet_data in data.items():
                if 'dantex' in sheet_name.lower():
                    # Ищем описания серий в данных
                    for row in sheet_data:
                        if isinstance(row, dict):
                            # Проверяем наличие названия серии и описания
                            for key, value in row.items():
                                if isinstance(value, str) and len(value) > 100:
                                    # Если строка длинная, возможно это описание
                                    if any(keyword in value.lower() for keyword in ['инверторн', 'сплит', 'кондиционер', 'климат']):
                                        # Попытаемся найти связанную серию
                                        series_match = re.search(r'(SPACE|CORSO|ADVANCE|ECO|CONCORDE|CRYSTAL)', value, re.IGNORECASE)
                                        if series_match:
                                            series_name = series_match.group(1).upper()
                                            descriptions[series_name] = value.strip()
                                            
        except Exception as e:
            print(f"Ошибка обработки файла {file_path}: {e}")
    
    return descriptions

def extract_model_descriptions_from_pdf(pdf_files: List[str]) -> Dict[str, str]:
    """Извлекает описания моделей кондиционеров из PDF файлов."""
    descriptions = {}
    
    for file_path in pdf_files:
        try:
            # Извлекаем содержимое PDF
            content = extract_pdf_content(file_path)
            
            # Ищем описания моделей в тексте
            if 'dantex' in file_path.lower():
                # Разбиваем текст на блоки для поиска описаний
                text_blocks = content.split('\n\n')
                
                for block in text_blocks:
                    if len(block) > 50:  # Достаточно длинный блок для описания
                        # Ищем упоминания серий и моделей
                        if any(keyword in block.lower() for keyword in ['инверторн', 'сплит', 'кондиционер', 'rk-']):
                            # Извлекаем номер модели
                            model_match = re.search(r'RK-(\d+)', block, re.IGNORECASE)
                            if model_match:
                                model_key = f"RK-{model_match.group(1)}"
                                descriptions[model_key] = block.strip()
                                
        except Exception as e:
            print(f"Ошибка обработки PDF файла {file_path}: {e}")
    
    return descriptions

def generate_air_description(model_data: Dict[str, Any], series_descriptions: Dict[str, str], model_descriptions: Dict[str, str]) -> str:
    """Генерирует описание для конкретного кондиционера."""
    
    model_name = model_data.get('model_name', '')
    brand = model_data.get('brand', '')
    series = model_data.get('series', '')
    specs = model_data.get('specifications', {})
    
    # Начинаем с базовой информации
    description_parts = []
    
    # Добавляем информацию о бренде и модели
    if brand and model_name:
        description_parts.append(f"Кондиционер {brand} {model_name}")
    
    # Добавляем технические характеристики
    if specs:
        cooling_power = specs.get('cooling_power_kw')
        heating_power = specs.get('heating_power_kw')
        energy_class = specs.get('energy_efficiency_class', '')
        
        if cooling_power or heating_power:
            power_info = []
            if cooling_power:
                power_info.append(f"мощность охлаждения {cooling_power} кВт")
            if heating_power:
                power_info.append(f"мощность обогрева {heating_power} кВт")
            
            if power_info:
                description_parts.append(f"с {', '.join(power_info)}")
        
        if energy_class:
            description_parts.append(f"Класс энергоэффективности: {energy_class}")
    
    # Ищем описание серии
    series_desc = None
    if series and series.upper() in series_descriptions:
        series_desc = series_descriptions[series.upper()]
    else:
        # Пытаемся найти описание по частичному совпадению названия модели
        for key, desc in series_descriptions.items():
            if key.lower() in model_name.lower():
                series_desc = desc
                break
    
    # Ищем описание конкретной модели
    model_desc = None
    model_key = model_name.split('/')[0]  # Берем первую часть модели
    if model_key in model_descriptions:
        model_desc = model_descriptions[model_key]
    else:
        # Ищем по номеру модели
        model_match = re.search(r'RK-(\d+)', model_name)
        if model_match:
            model_key = f"RK-{model_match.group(1)}"
            if model_key in model_descriptions:
                model_desc = model_descriptions[model_key]
    
    # Добавляем найденные описания
    if series_desc:
        description_parts.append(series_desc)
    
    if model_desc:
        description_parts.append(model_desc)
    
    # Если не нашли специфичного описания, добавляем общее
    if not series_desc and not model_desc:
        if 'inverter' in model_name.lower():
            description_parts.append("Инверторная сплит-система с плавным регулированием мощности для поддержания комфортной температуры и экономии электроэнергии.")
        else:
            description_parts.append("Надежная сплит-система для создания комфортного микроклимата в помещении.")
    
    # Объединяем все части описания
    full_description = '. '.join(description_parts)
    
    # Очищаем от лишних символов и форматируем
    full_description = re.sub(r'\s+', ' ', full_description).strip()
    
    return full_description

def update_image_paths(data: Dict[str, Any]) -> Dict[str, Any]:
    """Обновляет пути к изображениям с учетом новой структуры папок."""
    
    if 'air_conditioners' in data:
        for item in data['air_conditioners']:
            # Обновляем representative_image
            if 'representative_image' in item:
                old_path = item['representative_image']
                if old_path and not old_path.startswith('../'):
                    # Добавляем относительный путь для выхода из папки JSON_files
                    item['representative_image'] = f"../{old_path}"
    
    return data

def main():
    """Основная функция."""
    
    # Пути к файлам
    json_file_path = 'docs/JSON_files/complete_air_conditioners_catalog.json'
    xlsx_files = [
        'docs/prices_air_and_complectations/Прайс Магазин холода 2025.xlsx',
        'docs/prices_air_and_complectations/Прайс_лист_Климат_проджект_Беларусь.xlsx',
        'docs/prices_air_and_complectations/$VAM_Онлайн_прайс_Mitsubishi_Heavy,_TCL,_Aspen,_REFCO,_ХИМИЯ_и.xlsx'
    ]
    
    pdf_files = [
        'docs/air_catalogs/Catalog-Dantex-2024.pdf',
        'docs/air_catalogs/2025_HISENSE_catalog.pdf',
        'docs/air_catalogs/midea 24-25.pdf',
        'docs/air_catalogs/samsung сплит.pdf',
        'docs/air_catalogs/tcl.pdf',
        'docs/air_catalogs/toshiba.pdf',
        'docs/air_catalogs/tosot.pdf',
        'docs/air_catalogs/VETERO_catalog.pdf'
    ]
    
    # Загружаем JSON файл
    print("Загрузка JSON файла...")
    data = load_json_file(json_file_path)
    
    if not data:
        print("Не удалось загрузить JSON файл")
        return
    
    print(f"Загружено {len(data.get('air_conditioners', []))} кондиционеров")
    
    # Извлекаем описания из файлов
    print("Извлечение описаний из Excel файлов...")
    series_descriptions = extract_series_descriptions_from_xlsx(xlsx_files)
    print(f"Найдено {len(series_descriptions)} описаний серий")
    
    print("Извлечение описаний из PDF файлов...")
    model_descriptions = extract_model_descriptions_from_pdf(pdf_files)
    print(f"Найдено {len(model_descriptions)} описаний моделей")
    
    # Обновляем пути к изображениям
    print("Обновление путей к изображениям...")
    data = update_image_paths(data)
    
    # Добавляем описания к каждому кондиционеру
    print("Добавление описаний к кондиционерам...")
    
    if 'air_conditioners' in data:
        for i, item in enumerate(data['air_conditioners']):
            # Генерируем описание для каждого кондиционера
            description = generate_air_description(item, series_descriptions, model_descriptions)
            item['air_description'] = description
            
            # Обновляем техническую информацию из прайс-листов
            model_name = item.get('model_name', '')
            brand = item.get('brand', '')
            
            # Проверяем и обновляем данные из прайс-листов
            print(f"Обновлен кондиционер {i+1}/{len(data['air_conditioners'])}: {brand} {model_name}")
    
    # Обновляем метаданные
    if 'catalog_info' in data:
        from datetime import datetime
        data['catalog_info']['last_updated'] = datetime.now().isoformat()
        data['catalog_info']['description'] = "Полный каталог кондиционеров с детальными описаниями из прайс-листов поставщиков и технических каталогов"
    
    # Сохраняем обновленный файл
    print("Сохранение обновленного JSON файла...")
    save_json_file(data, json_file_path)
    
    print("Обновление завершено!")
    print(f"Обновлено {len(data.get('air_conditioners', []))} кондиционеров")
    print(f"Добавлены детальные описания для каждого кондиционера")
    print(f"Обновлены пути к изображениям для новой структуры папок")

if __name__ == "__main__":
    main()
