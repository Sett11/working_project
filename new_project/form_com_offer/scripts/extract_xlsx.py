import os
import pandas as pd
import json
from datetime import datetime
import numpy as np

# Кастомный сериалайзатор JSON
def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (np.datetime64, pd.Timestamp)):
        return str(obj)
    elif isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj) if not pd.isna(obj) else None
    elif pd.isna(obj):
        return None
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# Путь к директории с файлами
base_path = 'C:/Users/Lenovo/Desktop/development/working_project/new_project/form_com_offer/docs'
prices_path = os.path.join(base_path, 'prices_air_and_complectations')

# Список файлов XLSX
xlsx_files = [
    '$VAM_Онлайн_прайс_Mitsubishi_Heavy,_TCL,_Aspen,_REFCO,_ХИМИЯ_и.xlsx',
    'Прайс Магазин холода 2025.xlsx',
    'Прайс_лист_Климат_проджект_Беларусь.xlsx',
    'Прайс_лист_Климат_проджект_Беларусь_1.xlsx',
    'стоимости материалов кондиц.xlsx'
]

# Функция для извлечения данных из XLSX и их преобразования в словарь
def extract_xlsx_data(file_path):
    try:
        print(f"Обрабатываем файл: {file_path}")
        # Попробуем прочитать все листы
        excel_file = pd.ExcelFile(file_path)
        all_sheets_data = []
        
        for sheet_name in excel_file.sheet_names:
            print(f"  Читаем лист: {sheet_name}")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheet_data = df.to_dict(orient='records')
            # Добавляем информацию о источнике
            for record in sheet_data:
                record['_source_file'] = os.path.basename(file_path)
                record['_source_sheet'] = sheet_name
            all_sheets_data.extend(sheet_data)
        
        return all_sheets_data
    except Exception as e:
        print(f"Ошибка при обработке файла {file_path}: {e}")
        return []

# Обработка всех файлов и сбор данных о кондиционерах
all_data = []

# Автоматически найдем все XLSX файлы
for filename in os.listdir(prices_path):
    if filename.endswith('.xlsx'):
        full_path = os.path.join(prices_path, filename)
        print(f"Найден файл: {full_path}")
        data = extract_xlsx_data(full_path)
        all_data.extend(data)

print(f"Всего записей собрано: {len(all_data)}")

# Сохранение данных в файл JSON
output_path = os.path.join(base_path, 'air_conditioners_data.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=4, default=json_serializer)

print(f"Данные сохранены в: {output_path}")

