#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для перевода описаний кондиционеров с английского на русский язык
Переводит поля "description" в файле new_airs.json
"""

import json
import os
from typing import Dict, Any, List

def translate_description(english_text: str) -> str:
    """
    Переводит английское описание на русский язык
    
    Args:
        english_text: Текст на английском языке
        
    Returns:
        Переведенный текст на русском языке
    """
    
    # Словарь переводов для технических терминов
    translations = {
        "TCL split-system with modern design and energy saving functions": 
            "Сплит-система TCL с современным дизайном и функциями энергосбережения",
        
        "Mitsubishi Heavy Industries conditioner with extended warranty": 
            "Кондиционер Mitsubishi Heavy Industries с расширенной гарантией",
        
        "Mitsubishi Heavy Industries semi-commercial conditioner with 3-year warranty": 
            "Полупромышленный кондиционер Mitsubishi Heavy Industries с 3-летней гарантией"
    }
    
    # Если есть точное совпадение в словаре, используем его
    if english_text in translations:
        return translations[english_text]
    
    # Если нет точного совпадения, возвращаем оригинальный текст
    # (в данном случае это не должно произойти, так как у нас всего 3 уникальных описания)
    return english_text

def process_new_airs_file():
    """
    Обрабатывает файл new_airs.json, переводя все описания на русский язык
    """
    
    input_file = "new_airs.json"
    output_file = "new_airs_translated.json"
    
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
        
        # Собираем статистику по уникальным описаниям
        unique_descriptions = {}
        for ac in air_conditioners:
            desc = ac.get("description", "")
            unique_descriptions[desc] = unique_descriptions.get(desc, 0) + 1
        
        print(f"📝 Уникальных описаний: {len(unique_descriptions)}")
        for desc, count in unique_descriptions.items():
            print(f"   - '{desc}': {count} раз")
        
        # Переводим описания
        print("\n🔄 Переводим описания на русский язык...")
        translated_count = 0
        
        for i, ac in enumerate(air_conditioners):
            if i % 50 == 0:  # Показываем прогресс каждые 50 записей
                print(f"   Обработано: {i}/{len(air_conditioners)}")
            
            if "description" in ac:
                original_desc = ac["description"]
                translated_desc = translate_description(original_desc)
                
                if translated_desc != original_desc:
                    ac["description"] = translated_desc
                    translated_count += 1
        
        print(f"✅ Переведено описаний: {translated_count}")
        
        # Записываем результат
        print(f"💾 Записываем результат в {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Успешно! Создан файл {output_file}")
        
        # Показываем примеры переводов
        print(f"\n📋 Примеры переводов:")
        for i, ac in enumerate(air_conditioners[:3]):  # Показываем первые 3
            print(f"   {i+1}. ID {ac['id']}: {ac['description']}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def main():
    """
    Основная функция программы
    """
    print("🚀 Запуск скрипта перевода описаний на русский язык")
    print("=" * 60)
    
    success = process_new_airs_file()
    
    if success:
        print("\n🎉 Перевод выполнен успешно!")
        print("📁 Результат сохранен в файл: new_airs_translated.json")
    else:
        print("\n💥 Произошла ошибка при выполнении перевода!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
