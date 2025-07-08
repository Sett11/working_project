import json
import os
import math

def fix_nan_in_json(file_path):
    """
    Исправляет значения NaN в JSON-файле, заменяя их на None (null в JSON).
    
    Args:
        file_path (str): Путь к JSON-файлу для исправления
    """
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        return False
    
    try:
        print(f"Чтение файла: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Заменяем все вхождения NaN на null в строке
        # Это нужно делать перед парсингом JSON, так как NaN не является валидным JSON
        content = content.replace('NaN', 'null')
        
        # Теперь парсим исправленный JSON
        data = json.loads(content)
        
        # Проверяем и исправляем данные (дополнительная проверка)
        if isinstance(data, list):
            for item in data:
                fix_nan_in_object(item)
        elif isinstance(data, dict):
            fix_nan_in_object(data)
        
        # Сохраняем исправленный файл
        backup_path = file_path + '.backup'
        print(f"Создание резервной копии: {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content.replace('null', 'NaN'))  # Восстанавливаем оригинал в бэкапе
        
        print(f"Сохранение исправленного файла: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("✓ Файл успешно исправлен!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"Ошибка при парсинге JSON: {e}")
        return False
    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")
        return False

def fix_nan_in_object(obj):
    """
    Рекурсивно исправляет значения NaN в объекте, заменяя их на None.
    
    Args:
        obj: Объект для обработки (dict, list, или другой тип)
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, float) and math.isnan(value):
                obj[key] = None
            elif isinstance(value, (dict, list)):
                fix_nan_in_object(value)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, float) and math.isnan(item):
                obj[i] = None
            elif isinstance(item, (dict, list)):
                fix_nan_in_object(item)

def main():
    """
    Основная функция для запуска скрипта.
    """
    file_path = "docs/JSON_files/complete_air_conditioners_catalog.json"
    
    print("=" * 60)
    print("Скрипт исправления NaN значений в JSON-файле")
    print("=" * 60)
    
    if fix_nan_in_json(file_path):
        print("\n✓ Скрипт завершён успешно!")
        print(f"✓ Исправленный файл: {file_path}")
        print(f"✓ Резервная копия: {file_path}.backup")
    else:
        print("\n✗ Скрипт завершён с ошибкой!")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
