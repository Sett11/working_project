import json
import os

# Абсолютный путь к файлу
file_path = os.path.abspath('docs/airs_catalog.json')
print(f"Работаем с файлом: {file_path}")

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data.get('air_conditioners', []))
    print(f'Изначальное количество кондиционеров: {original_count}')

    # Фильтрация
    cleaned_air_conditioners = [
        ac for ac in data.get('air_conditioners', [])
        if (ac.get('pricing') and 
            ac['pricing'].get('retail_price_byn') and 
            isinstance(ac['pricing']['retail_price_byn'], (int, float)) and 
            ac['pricing']['retail_price_byn'] > 0 and
            ac.get('suppliers') and 
            isinstance(ac['suppliers'], list) and 
            len(ac['suppliers']) > 0)
    ]
    
    data['air_conditioners'] = cleaned_air_conditioners
    cleaned_count = len(data['air_conditioners'])
    
    print(f'Количество кондиционеров после очистки: {cleaned_count}')
    print(f'Удалено: {original_count - cleaned_count} записей')

    # Сохранение
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f'Файл {file_path} успешно очищен и перезаписан.')

except FileNotFoundError:
    print(f"Ошибка: Файл не найден по пути {file_path}")
except json.JSONDecodeError:
    print(f"Ошибка: Не удалось декодировать JSON из файла {file_path}")
except Exception as e:
    print(f"Произошла непредвиденная ошибка: {e}")

