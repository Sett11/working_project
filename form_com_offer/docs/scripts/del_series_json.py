#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для удаления поля "series" из JSON файлов airs.json и new_airs.json
Удаляет поле "series" у всех объектов-кондиционеров, оставляя остальные поля без изменений
"""

import json
import os
from typing import Dict, Any, List

def remove_series_field(ac_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Удаляет поле "series" из объекта кондиционера
    
    Args:
        ac_dict: Словарь с данными кондиционера
        
    Returns:
        Словарь без поля "series"
    """
    if "series" in ac_dict:
        del ac_dict["series"]
    return ac_dict

def process_json_file(input_file: str, output_file: str = None) -> bool:
    """
    Обрабатывает JSON файл, удаляя поле "series" у всех кондиционеров
    
    Args:
        input_file: Путь к входному файлу
        output_file: Путь к выходному файлу (если None, то перезаписывает входной)
        
    Returns:
        True если успешно, False если ошибка
    """
    
    if output_file is None:
        output_file = input_file
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"❌ Ошибка: Файл {input_file} не найден!")
        return False
    
    try:
        # Читаем исходный файл
        print(f"📖 Читаем файл {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем структуру данных
        if "air_conditioners" not in data:
            print(f"❌ Ошибка: В файле {input_file} отсутствует ключ 'air_conditioners'!")
            return False
        
        air_conditioners = data["air_conditioners"]
        print(f"📊 Найдено кондиционеров: {len(air_conditioners)}")
        
        # Удаляем поле "series" у каждого кондиционера
        print("🗑️  Удаляем поле 'series'...")
        processed_count = 0
        
        for i, ac in enumerate(air_conditioners):
            if i % 100 == 0:  # Показываем прогресс каждые 100 записей
                print(f"   Обработано: {i}/{len(air_conditioners)}")
            
            # Удаляем поле "series" если оно есть
            if "series" in ac:
                del ac["series"]
                processed_count += 1
        
        print(f"✅ Удалено полей 'series': {processed_count}")
        
        # Записываем результат
        print(f"💾 Записываем результат в {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Успешно обработан файл {output_file}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON в файле {input_file}: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка при обработке {input_file}: {e}")
        return False

def main():
    """
    Основная функция программы
    """
    print("🚀 Запуск скрипта удаления поля 'series'")
    print("=" * 50)
    
    # Список файлов для обработки
    files_to_process = [
        "airs.json",
        "new_airs.json"
    ]
    
    success_count = 0
    total_files = len(files_to_process)
    
    for file_name in files_to_process:
        print(f"\n📁 Обрабатываем файл: {file_name}")
        print("-" * 30)
        
        if process_json_file(file_name):
            success_count += 1
        else:
            print(f"❌ Не удалось обработать файл {file_name}")
    
    print("\n" + "=" * 50)
    print(f"📈 Итоговая статистика:")
    print(f"   - Обработано файлов: {success_count}/{total_files}")
    
    if success_count == total_files:
        print("🎉 Все файлы обработаны успешно!")
        return 0
    else:
        print("💥 Некоторые файлы не удалось обработать!")
        return 1

if __name__ == "__main__":
    exit(main())
