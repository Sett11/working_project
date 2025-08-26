#!/usr/bin/env python3
"""
Скрипт валидации каталога компонентов.
Проверяет уникальность ID и имен компонентов перед запуском приложения.
"""

import json
import os
import sys
from collections import defaultdict

def validate_components_catalog(catalog_path):
    """
    Валидирует каталог компонентов на наличие дубликатов и уникальных ID.
    
    Args:
        catalog_path: Путь к файлу каталога компонентов
    
    Returns:
        bool: True если каталог валиден, False если есть ошибки
    """
    try:
        with open(catalog_path, encoding='utf-8') as f:
            catalog_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл каталога не найден: {catalog_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка: Неверный формат JSON в файле {catalog_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при чтении файла {catalog_path}: {e}")
        return False
    
    if not catalog_data or "components" not in catalog_data:
        print("❌ Ошибка: Каталог компонентов пуст или не содержит секцию 'components'")
        return False
    
    components = catalog_data["components"]
    if not components:
        print("⚠️  Предупреждение: Каталог компонентов пуст")
        return True
    
    print(f"📋 Проверяем каталог компонентов: {len(components)} компонентов")
    
    # Проверяем наличие уникальных ID
    component_ids = []
    component_names = []
    missing_ids = []
    duplicate_ids = []
    duplicate_names = []
    
    for i, comp in enumerate(components):
        comp_id = comp.get("id")
        comp_name = comp.get("name", "")
        
        if not comp_id:
            missing_ids.append(f"Индекс {i}: '{comp_name}'")
        else:
            if comp_id in component_ids:
                duplicate_ids.append(str(comp_id))
            else:
                component_ids.append(comp_id)
        
        if comp_name in component_names:
            duplicate_names.append(comp_name)
        else:
            component_names.append(comp_name)
    
    # Выводим результаты проверки
    has_errors = False
    
    if missing_ids:
        print(f"❌ Компоненты без ID ({len(missing_ids)}):")
        for missing in missing_ids:
            print(f"   - {missing}")
        has_errors = True
    
    if duplicate_ids:
        print(f"❌ Дублирующиеся ID ({len(duplicate_ids)}):")
        for dup_id in duplicate_ids:
            print(f"   - ID: {dup_id}")
        has_errors = True
    
    if duplicate_names:
        print(f"❌ Дублирующиеся имена ({len(duplicate_names)}):")
        for dup_name in duplicate_names:
            print(f"   - '{dup_name}'")
        has_errors = True
    
    if not has_errors:
        print("✅ Каталог компонентов валиден!")
        print(f"   - Уникальных компонентов: {len(components)}")
        print(f"   - Уникальных ID: {len(component_ids)}")
        print(f"   - Уникальных имен: {len(component_names)}")
    
    return not has_errors

def main():
    """Основная функция скрипта"""
    # Путь к каталогу компонентов
    script_dir = os.path.dirname(os.path.abspath(__file__))
    catalog_path = os.path.join(script_dir, 'docs', 'components_catalog.json')
    
    print("🔍 Валидация каталога компонентов")
    print(f"📁 Путь к каталогу: {catalog_path}")
    print("-" * 50)
    
    # Выполняем валидацию
    is_valid = validate_components_catalog(catalog_path)
    
    print("-" * 50)
    if is_valid:
        print("✅ Валидация завершена успешно")
        sys.exit(0)
    else:
        print("❌ Валидация завершена с ошибками")
        print("💡 Исправьте ошибки в каталоге компонентов перед запуском приложения")
        sys.exit(1)

if __name__ == "__main__":
    main()
