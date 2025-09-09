#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления ID кондиционеров в файле airs.json
Начинает с ID 1 и продолжает по порядку: 1, 2, 3, 4...
"""

import json
import os
import sys
from pathlib import Path

def update_airs_ids():
    """
    Обновляет ID всех кондиционеров в файле airs.json
    Начинает с ID 1 и продолжает по порядку
    """
    
    # Путь к файлу airs.json
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    airs_file = project_root / "docs" / "airs.json"
    
    print(f"🔍 Обрабатываем файл: {airs_file}")
    
    # Проверяем существование файла
    if not airs_file.exists():
        print(f"❌ Файл {airs_file} не найден!")
        return False
    
    try:
        # Читаем файл
        print("📖 Читаем файл airs.json...")
        with open(airs_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем структуру данных
        if not isinstance(data, dict) or 'air_conditioners' not in data:
            print("❌ Неверная структура файла! Ожидается объект с ключом 'air_conditioners'")
            return False
        
        air_conditioners = data['air_conditioners']
        if not isinstance(air_conditioners, list):
            print("❌ Поле 'air_conditioners' должно быть массивом!")
            return False
        
        print(f"📊 Найдено кондиционеров: {len(air_conditioners)}")
        
        # Обновляем ID, начиная с 1
        start_id = 1
        updated_count = 0
        
        print(f"🔄 Обновляем ID, начиная с {start_id}...")
        
        for i, conditioner in enumerate(air_conditioners):
            if not isinstance(conditioner, dict):
                print(f"⚠️  Пропускаем элемент {i}: не является объектом")
                continue
            
            old_id = conditioner.get('id')
            new_id = start_id + i
            
            conditioner['id'] = new_id
            updated_count += 1
            
            if i < 5:  # Показываем первые 5 изменений для примера
                print(f"   ID {old_id} → {new_id}")
            elif i == 5:
                print("   ...")
        
        print(f"✅ Обновлено ID для {updated_count} кондиционеров")
        
        # Создаем резервную копию
        backup_file = airs_file.with_suffix('.json.backup')
        print(f"💾 Создаем резервную копию: {backup_file}")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Сохраняем обновленный файл
        print("💾 Сохраняем обновленный файл...")
        with open(airs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("🎉 Готово! ID кондиционеров успешно обновлены")
        print(f"📈 Диапазон ID: {start_id} - {start_id + updated_count - 1}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 Скрипт обновления ID кондиционеров в airs.json")
    print("=" * 60)
    
    success = update_airs_ids()
    
    if success:
        print("\n✅ Скрипт выполнен успешно!")
        sys.exit(0)
    else:
        print("\n❌ Скрипт завершился с ошибкой!")
        sys.exit(1)

if __name__ == "__main__":
    main()
