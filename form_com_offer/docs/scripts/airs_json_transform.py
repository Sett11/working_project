#!/usr/bin/env python3
"""
Скрипт для трансформации файла airs.json

Функции:
1. Убирает поле "class" у всех кондиционеров
2. Фильтрует кондиционеры по критериям:
   - model_name = "moke"
   - series содержит "Колонный"
3. Сохраняет результат в new_airs.json
"""

import json
import os
from pathlib import Path

def transform_airs_data(input_file: str, output_file: str):
    """
    Трансформирует данные из airs.json в new_airs.json
    
    Args:
        input_file (str): Путь к входному файлу airs.json
        output_file (str): Путь к выходному файлу new_airs.json
    """
    
    # Проверяем существование входного файла
    if not os.path.exists(input_file):
        print(f"❌ Ошибка: Файл {input_file} не найден")
        return False
    
    try:
        # Читаем исходный файл
        print(f"📖 Читаю файл {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Получаем список кондиционеров из правильной структуры
        if "air_conditioners" in json_data:
            airs_data = json_data["air_conditioners"]
        else:
            # Если структура другая, пытаемся использовать весь файл как список
            airs_data = json_data if isinstance(json_data, list) else []
        
        print(f"✅ Прочитано {len(airs_data)} кондиционеров")
        
        # Фильтруем и трансформируем данные
        filtered_airs = []
        removed_count = 0
        seen_model_names = set()  # Для отслеживания уникальных model_name
        
        for air in airs_data:
            # Проверяем критерии фильтрации
            should_remove = False
            
            # Критерий 1: model_name = "moke"
            if air.get("model_name") == "moke":
                should_remove = True
                print(f"🚫 Удаляю: model_name = 'moke' - {air.get('model_name', 'N/A')}")
            
            # Критерий 2: series содержит "Колонный"
            elif "Колонный" in air.get("series", ""):
                should_remove = True
                print(f"🚫 Удаляю: series содержит 'Колонный' - {air.get('series', 'N/A')}")
            
            # Критерий 3: model_name пустой
            elif air.get("model_name") == "":
                should_remove = True
                print(f"🚫 Удаляю: model_name пустой - '{air.get('model_name', 'N/A')}'")
            
            # Критерий 4: model_name уже встречался (дублирование)
            elif air.get("model_name") in seen_model_names:
                should_remove = True
                print(f"🚫 Удаляю: дубликат model_name - {air.get('model_name', 'N/A')}")
            
            if should_remove:
                removed_count += 1
                continue
            
            # Трансформируем: убираем поле "class"
            if "class" in air:
                del air["class"]
            
            # Добавляем в отфильтрованный список и запоминаем model_name
            filtered_airs.append(air)
            seen_model_names.add(air.get("model_name"))
        
        # Перенумеровываем ID для отфильтрованных кондиционеров
        print(f"🔄 Перенумеровываю ID кондиционеров...")
        for i, air in enumerate(filtered_airs, 1):
            air["id"] = i
        
        print(f"✅ Отфильтровано: {len(filtered_airs)} кондиционеров")
        print(f"🚫 Удалено: {removed_count} кондиционеров")
        
        # Сохраняем результат в той же структуре
        print(f"💾 Сохраняю результат в {output_file}...")
        result_data = {"air_conditioners": filtered_airs}
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Файл {output_file} успешно создан!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка: Невалидный JSON в файле {input_file}: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при обработке файла: {e}")
        return False

def main():
    """Основная функция"""
    
    # Определяем пути к файлам
    current_dir = Path(__file__).parent
    input_file = current_dir / "airs.json"
    output_file = current_dir / "new_airs.json"
    
    print("🚀 Запуск трансформации airs.json...")
    print(f"📁 Рабочая директория: {current_dir}")
    print(f"📥 Входной файл: {input_file}")
    print(f"📤 Выходной файл: {output_file}")
    print("-" * 50)
    
    # Запускаем трансформацию
    success = transform_airs_data(str(input_file), str(output_file))
    
    if success:
        print("-" * 50)
        print("🎉 Трансформация завершена успешно!")
    else:
        print("-" * 50)
        print("💥 Трансформация завершена с ошибками!")

if __name__ == "__main__":
    main()
