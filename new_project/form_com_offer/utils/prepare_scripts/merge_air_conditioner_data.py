import os
import json
import re
import math
from datetime import datetime
from typing import Dict, List, Any, Optional

def clean_text(text: str) -> str:
    """Очищает текст от лишних символов и пробелов"""
    if not text or text in ['NaN', 'nan', None]:
        return ""
    return str(text).strip().replace('\n', ' ').replace('\r', '')

def sanitize_json_data(data: Any) -> Any:
    """Recursively sanitizes data to replace NaN, inf, and other non-JSON values"""
    if isinstance(data, dict):
        return {k: sanitize_json_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_data(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    elif data in ['NaN', 'nan', 'inf', '-inf']:
        return None
    else:
        return data

def extract_power_from_text(text: str) -> Optional[float]:
    """Извлекает мощность из текста (например, '2,5 (0,5-3,25)' -> 2.5)"""
    if not text:
        return None
    
    # Ищем число в начале строки
    match = re.search(r'^(\d+(?:[,\.]\d+)?)', str(text))
    if match:
        power_str = match.group(1).replace(',', '.')
        try:
            return float(power_str)
        except ValueError:
            return None
    return None

def extract_price_from_text(text: str) -> Optional[float]:
    """Извлекает цену из текста (например, '560$' -> 560.0)"""
    if not text:
        return None
    
    # Убираем символы валют и извлекаем число
    price_text = str(text).replace('$', '').replace('р.', '').replace('руб', '').strip()
    try:
        return float(price_text.replace(',', '.'))
    except (ValueError, AttributeError):
        return None

def normalize_model_name(model_name: str) -> str:
    """Нормализует название модели для сопоставления"""
    if not model_name:
        return ""
    
    # Убираем лишние символы и приводим к нижнему регистру
    normalized = re.sub(r'[^\w\d-]', '', str(model_name).lower())
    return normalized

def extract_model_info_from_xlsx_row(row: Dict) -> Optional[Dict]:
    """Извлекает информацию о модели из строки XLSX данных"""
    # Ищем название модели в основных полях
    model_name = None
    for field in ['OOO "МАГАЗИН ХОЛОДА"', 'Unnamed: 1', 'Модель']:
        if field in row and row[field] and row[field] not in ['NaN', 'nan', None]:
            potential_model = clean_text(str(row[field]))
            # Проверяем, что это похоже на название модели (содержит буквы и цифры)
            if re.search(r'[A-Za-z].*\d|RK-\d+', potential_model):
                model_name = potential_model
                break
    
    if not model_name:
        return None
    
    # Извлекаем характеристики
    cooling_power = None
    heating_power = None
    cooling_consumption = None
    heating_consumption = None
    dealer_price_usd = None
    retail_price_usd = None
    retail_price_byn = None
    
    # Ищем мощности охлаждения и обогрева
    for field, value in row.items():
        if 'холод' in str(field).lower() and 'производительность' in str(field).lower():
            cooling_power = extract_power_from_text(str(value))
        elif 'тепло' in str(field).lower() and 'производительность' in str(field).lower():
            heating_power = extract_power_from_text(str(value))
        elif 'холод' in str(field).lower() and 'потребляемая' in str(field).lower():
            cooling_consumption = extract_power_from_text(str(value))
        elif 'тепло' in str(field).lower() and 'потребляемая' in str(field).lower():
            heating_consumption = extract_power_from_text(str(value))
        elif 'дилер' in str(field).lower() and 'usd' in str(field).lower():
            dealer_price_usd = extract_price_from_text(str(value))
        elif 'розница' in str(field).lower() and 'usd' in str(field).lower():
            retail_price_usd = extract_price_from_text(str(value))
        elif 'розница' in str(field).lower() and 'byn' in str(field).lower():
            retail_price_byn = extract_price_from_text(str(value))
    
    # Альтернативный поиск мощностей по индексам колонок
    if not cooling_power and 'Unnamed: 2' in row:
        cooling_power = extract_power_from_text(str(row['Unnamed: 2']))
    if not heating_power and 'Unnamed: 3' in row:
        heating_power = extract_power_from_text(str(row['Unnamed: 3']))
    if not cooling_consumption and 'Unnamed: 4' in row:
        cooling_consumption = extract_power_from_text(str(row['Unnamed: 4']))
    if not heating_consumption and 'Unnamed: 5' in row:
        heating_consumption = extract_power_from_text(str(row['Unnamed: 5']))
    if not dealer_price_usd and 'Unnamed: 8' in row:
        dealer_price_usd = extract_price_from_text(str(row['Unnamed: 8']))
    if not retail_price_usd and 'Unnamed: 9' in row:
        retail_price_usd = extract_price_from_text(str(row['Unnamed: 9']))
    if not retail_price_byn and 'Unnamed: 10' in row:
        retail_price_byn = extract_price_from_text(str(row['Unnamed: 10']))
    
    # Определяем серию и бренд
    series_name = ""
    brand = ""
    
    # Ищем серию в предыдущих строках или текущей
    for field, value in row.items():
        value_str = str(value).lower()
        if 'сплит-система' in value_str or 'серия' in value_str:
            series_name = clean_text(str(value))
            break
    
    # Определяем бренд из источника
    source_file = row.get('_source_file', '')
    if 'dantex' in source_file.lower():
        brand = "DANTEX"
    elif 'hisense' in source_file.lower():
        brand = "HISENSE"
    elif 'midea' in source_file.lower():
        brand = "MIDEA"
    elif 'electrolux' in source_file.lower():
        brand = "ELECTROLUX"
    elif 'магазин холода' in source_file.lower():
        # Пытаемся определить бренд из контекста
        if 'dantex' in str(row).lower():
            brand = "DANTEX"
        elif any(keyword in str(row).lower() for keyword in ['vetero', 'marsa', 'alpicair']):
            brand = "VARIOUS"
    
    return {
        'model': model_name,
        'brand': brand,
        'series': series_name,
        'cooling_power_kw': cooling_power,
        'heating_power_kw': heating_power,
        'cooling_consumption_kw': cooling_consumption,
        'heating_consumption_kw': heating_consumption,
        'dealer_price_usd': dealer_price_usd,
        'retail_price_usd': retail_price_usd,
        'retail_price_byn': retail_price_byn,
        'source_file': row.get('_source_file', ''),
        'source_sheet': row.get('_source_sheet', ''),
        'pipe_diameter': clean_text(str(row.get('Unnamed: 6', ''))),
        'energy_efficiency': clean_text(str(row.get('Unnamed: 7', '')))
    }

def find_matching_pdf_info(model_name: str, pdf_data: List[Dict]) -> Dict:
    """Находит соответствующую информацию в PDF данных"""
    normalized_model = normalize_model_name(model_name)
    
    for pdf_file in pdf_data:
        text_content = str(pdf_file.get('text_content', '')).lower()
        
        # Проверяем, упоминается ли модель в тексте
        if normalized_model in text_content.replace('-', '').replace(' ', ''):
            return {
                'pdf_source': pdf_file.get('file_name', ''),
                'description': extract_description_for_model(model_name, text_content),
                'available_images': len(pdf_file.get('images', []))
            }
    
    return {}

def extract_description_for_model(model_name: str, text_content: str) -> str:
    """Извлекает описание для конкретной модели из текста PDF"""
    # Ищем абзацы, которые могут содержать описание модели
    paragraphs = text_content.split('\n')
    
    relevant_paragraphs = []
    for paragraph in paragraphs:
        if any(keyword in paragraph.lower() for keyword in [
            model_name.lower().replace('-', ''), 
            'кондиционер', 
            'сплит-система',
            'охлаждение',
            'мощность'
        ]):
            cleaned = paragraph.strip()
            if len(cleaned) > 50:  # Только содержательные абзацы
                relevant_paragraphs.append(cleaned)
    
    return ' '.join(relevant_paragraphs[:3])  # Берем первые 3 релевантных абзаца

def assign_representative_image(model_info: Dict, images_path: str) -> Optional[str]:
    """Назначает репрезентативное изображение для модели"""
    if not model_info.get('brand'):
        return None
    
    brand = model_info['brand'].lower()
    model = model_info.get('model', '').lower()
    
    # Ищем изображения, связанные с брендом модели
    try:
        image_files = os.listdir(images_path)
        
        # Приоритет изображениям с названием модели
        for img_file in image_files:
            img_lower = img_file.lower()
            if model in img_lower and brand in img_lower:
                return f"images/{img_file}"
        
        # Если точного совпадения нет, ищем по бренду
        brand_images = [f for f in image_files if brand in f.lower()]
        if brand_images:
            # Берем первое подходящее изображение
            return f"images/{brand_images[0]}"
    
    except FileNotFoundError:
        pass
    
    return None

def merge_air_conditioner_data():
    """Главная функция объединения данных о кондиционерах"""
    
    print("🔄 Начинаем объединение данных о кондиционерах...")
    
    # Пути к файлам
    base_path = 'C:/Users/Lenovo/Desktop/development/working_project/new_project/form_com_offer/docs'
    xlsx_file = os.path.join(base_path, 'air_conditioners_data.json')
    pdf_file = os.path.join(base_path, 'pdf_data.json')
    images_path = os.path.join(base_path, 'images')
    output_file = os.path.join(base_path, 'complete_air_conditioners_catalog.json')
    
    # Загружаем данные
    print("📂 Загружаем данные из XLSX...")
    with open(xlsx_file, 'r', encoding='utf-8') as f:
        xlsx_data = json.load(f)
    
    print("📂 Загружаем данные из PDF...")
    with open(pdf_file, 'r', encoding='utf-8') as f:
        pdf_data = json.load(f)
    
    print(f"📊 Обрабатываем {len(xlsx_data)} записей из XLSX файлов...")
    
    # Словарь для хранения уникальных моделей
    unique_models = {}
    suppliers_info = {}
    
    # Обрабатываем данные из XLSX
    for row in xlsx_data:
        model_info = extract_model_info_from_xlsx_row(row)
        
        if model_info and model_info['model']:
            model_key = normalize_model_name(model_info['model'])
            
            if model_key not in unique_models:
                # Ищем дополнительную информацию в PDF
                pdf_info = find_matching_pdf_info(model_info['model'], pdf_data)
                
                # Назначаем репрезентативное изображение
                representative_image = assign_representative_image(model_info, images_path)
                
                unique_models[model_key] = {
                    'id': len(unique_models) + 1,
                    'model_name': model_info['model'],
                    'brand': model_info['brand'],
                    'series': model_info['series'],
                    'specifications': {
                        'cooling_power_kw': model_info['cooling_power_kw'],
                        'heating_power_kw': model_info['heating_power_kw'],
                        'cooling_consumption_kw': model_info['cooling_consumption_kw'],
                        'heating_consumption_kw': model_info['heating_consumption_kw'],
                        'pipe_diameter': model_info['pipe_diameter'],
                        'energy_efficiency_class': model_info['energy_efficiency']
                    },
                    'pricing': {
                        'dealer_price_usd': model_info['dealer_price_usd'],
                        'retail_price_usd': model_info['retail_price_usd'],
                        'retail_price_byn': model_info['retail_price_byn']
                    },
                    'suppliers': [
                        {
                            'name': 'Магазин холода',
                            'source_file': model_info['source_file'],
                            'source_sheet': model_info['source_sheet'],
                            'dealer_price_usd': model_info['dealer_price_usd'],
                            'retail_price_usd': model_info['retail_price_usd'],
                            'retail_price_byn': model_info['retail_price_byn']
                        }
                    ],
                    'description': pdf_info.get('description', ''),
                    'pdf_source': pdf_info.get('pdf_source', ''),
                    'representative_image': representative_image,
                    'available_images_count': pdf_info.get('available_images', 0),
                    'last_updated': datetime.now().isoformat()
                }
            else:
                # Добавляем информацию от другого поставщика
                existing_model = unique_models[model_key]
                
                # Обновляем данные, если они отсутствуют
                if not existing_model['specifications']['cooling_power_kw'] and model_info['cooling_power_kw']:
                    existing_model['specifications']['cooling_power_kw'] = model_info['cooling_power_kw']
                
                if not existing_model['specifications']['heating_power_kw'] and model_info['heating_power_kw']:
                    existing_model['specifications']['heating_power_kw'] = model_info['heating_power_kw']
                
                # Добавляем нового поставщика, если цены отличаются
                new_supplier = {
                    'name': 'Дополнительный поставщик',
                    'source_file': model_info['source_file'],
                    'source_sheet': model_info['source_sheet'],
                    'dealer_price_usd': model_info['dealer_price_usd'],
                    'retail_price_usd': model_info['retail_price_usd'],
                    'retail_price_byn': model_info['retail_price_byn']
                }
                
                # Проверяем, что это действительно новый поставщик с отличающимися ценами
                is_different_supplier = True
                for supplier in existing_model['suppliers']:
                    if (supplier['dealer_price_usd'] == new_supplier['dealer_price_usd'] and
                        supplier['retail_price_usd'] == new_supplier['retail_price_usd']):
                        is_different_supplier = False
                        break
                
                if is_different_supplier:
                    existing_model['suppliers'].append(new_supplier)
    
    # Конвертируем в список для финального JSON
    final_catalog = {
        'catalog_info': {
            'name': 'Полный каталог кондиционеров',
            'description': 'Объединенный каталог кондиционеров из прайс-листов поставщиков и технических каталогов',
            'total_models': len(unique_models),
            'generated_at': datetime.now().isoformat(),
            'sources': {
                'xlsx_files_processed': len(set([row.get('_source_file', '') for row in xlsx_data])),
                'pdf_files_processed': len(pdf_data),
                'images_available': len(os.listdir(images_path)) if os.path.exists(images_path) else 0
            }
        },
        'air_conditioners': list(unique_models.values())
    }
    
    # Очищаем данные от NaN и infinity значений
    print("🧹 Очищаем данные от некорректных значений...")
    sanitized_catalog = sanitize_json_data(final_catalog)
    
    # Сохраняем результат
    print(f"💾 Сохраняем объединенный каталог в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sanitized_catalog, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Успешно создан объединенный каталог!")
    print(f"📈 Статистика:")
    print(f"   - Всего уникальных моделей: {len(unique_models)}")
    print(f"   - Обработано XLSX записей: {len(xlsx_data)}")
    print(f"   - Обработано PDF файлов: {len(pdf_data)}")
    print(f"   - Доступно изображений: {final_catalog['catalog_info']['sources']['images_available']}")
    
    # Показываем примеры обработанных моделей
    print(f"\n🔍 Примеры обработанных моделей:")
    for i, model in enumerate(list(unique_models.values())[:5]):
        print(f"   {i+1}. {model['brand']} {model['model_name']} - {len(model['suppliers'])} поставщик(ов)")
    
    return output_file

if __name__ == "__main__":
    merge_air_conditioner_data()
