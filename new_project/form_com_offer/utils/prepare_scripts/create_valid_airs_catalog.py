"""
Скрипт для создания валидного JSON-каталога кондиционеров на основе Excel-файлов.

Алгоритм:
1. Загружаем существующий airs_catalog.json
2. Загружаем все Excel-файлы из docs/prices_and_catalog
3. Для каждой модели из JSON ищем её в Excel-файлах
4. Обновляем данные модели актуальной информацией из Excel
5. Сохраняем валидированный каталог
"""
import json
import pandas as pd
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('create_valid_airs_catalog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ValidAirCatalogCreator:
    def __init__(self, json_path: str, excel_dir: str, output_path: str):
        """
        Инициализация создателя валидного каталога.
        
        Args:
            json_path: Путь к существующему JSON-каталогу
            excel_dir: Путь к папке с Excel-файлами
            output_path: Путь для сохранения валидированного каталога
        """
        self.json_path = json_path
        self.excel_dir = excel_dir
        self.output_path = output_path
        self.catalog_data = None
        self.excel_data = {}
        self.stats = {
            'total_models': 0,
            'found_in_excel': 0,
            'not_found': 0,
            'updated': 0,
            'removed': 0
        }
    
    def load_existing_catalog(self) -> bool:
        """Загружает существующий JSON-каталог."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.catalog_data = json.load(f)
            logger.info(f"Загружен существующий каталог с {len(self.catalog_data['air_conditioners'])} кондиционерами")
            self.stats['total_models'] = len(self.catalog_data['air_conditioners'])
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки JSON: {e}")
            return False
    
    def load_excel_files(self) -> bool:
        """Загружает все Excel-файлы в память."""
        try:
            excel_files = [f for f in os.listdir(self.excel_dir) if f.endswith('.xlsx')]
            logger.info(f"Найдено {len(excel_files)} Excel-файлов")
            
            for file_name in excel_files:
                file_path = os.path.join(self.excel_dir, file_name)
                logger.info(f"Загружаем файл: {file_name}")
                
                try:
                    # Читаем все листы из Excel-файла
                    excel_file = pd.ExcelFile(file_path)
                    
                    for sheet_name in excel_file.sheet_names:
                        try:
                            df = pd.read_excel(file_path, sheet_name=sheet_name)
                            if not df.empty:
                                # Добавляем информацию об источнике
                                df['_source_file'] = file_name
                                df['_source_sheet'] = sheet_name
                                
                                key = f"{file_name}_{sheet_name}"
                                self.excel_data[key] = df
                                logger.info(f"  Загружен лист: {sheet_name} ({len(df)} строк)")
                        except Exception as e:
                            logger.warning(f"  Ошибка чтения листа {sheet_name}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Ошибка чтения файла {file_name}: {e}")
                    continue
            
            total_sheets = len(self.excel_data)
            logger.info(f"Загружено {total_sheets} листов из Excel-файлов")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel-файлов: {e}")
            return False
    
    def normalize_model_name(self, model_name: str) -> str:
        """
        Нормализует название модели для поиска.
        
        Args:
            model_name: Исходное название модели
            
        Returns:
            Нормализованное название для поиска
        """
        if not model_name:
            return ""
        
        # Приводим к верхнему регистру и убираем лишние пробелы
        normalized = str(model_name).upper().strip()
        
        # Убираем лишние символы, но оставляем основные
        normalized = re.sub(r'[^\w\s\-/]', '', normalized)
        
        # Заменяем множественные пробелы на один
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def find_model_in_excel(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Ищет модель в Excel-данных с гибким поиском.
        
        Args:
            model_name: Название модели для поиска
            
        Returns:
            Словарь с найденными данными или None
        """
        normalized_search = self.normalize_model_name(model_name)
        
        if not normalized_search:
            return None
        
        # Разбиваем название модели на части для поиска
        search_parts = normalized_search.split()
        
        for key, df in self.excel_data.items():
            # Ищем во всех колонках
            for col in df.columns:
                if pd.api.types.is_string_dtype(df[col]):
                    # Нормализуем значения в колонке для поиска
                    normalized_values = df[col].astype(str).apply(self.normalize_model_name)
                    
                    # 1. Точное совпадение
                    exact_matches = normalized_values == normalized_search
                    if exact_matches.any():
                        row = df[exact_matches].iloc[0]
                        return {
                            'data': row.to_dict(),
                            'source_file': row.get('_source_file', ''),
                            'source_sheet': row.get('_source_sheet', ''),
                            'excel_key': key,
                            'match_type': 'exact'
                        }
                    
                    # 2. Поиск по подстроке
                    substring_matches = normalized_values.str.contains(normalized_search, na=False)
                    if substring_matches.any():
                        row = df[substring_matches].iloc[0]
                        return {
                            'data': row.to_dict(),
                            'source_file': row.get('_source_file', ''),
                            'source_sheet': row.get('_source_sheet', ''),
                            'excel_key': key,
                            'match_type': 'substring'
                        }
                    
                    # 3. Поиск по частям названия (хотя бы 2 части совпадают)
                    for i in range(len(search_parts) - 1):
                        for j in range(i + 2, len(search_parts) + 1):
                            search_part = ' '.join(search_parts[i:j])
                            if len(search_part) >= 3:  # Минимум 3 символа
                                part_matches = normalized_values.str.contains(search_part, na=False)
                                if part_matches.any():
                                    row = df[part_matches].iloc[0]
                                    return {
                                        'data': row.to_dict(),
                                        'source_file': row.get('_source_file', ''),
                                        'source_sheet': row.get('_source_sheet', ''),
                                        'excel_key': key,
                                        'match_type': 'partial'
                                    }
        
        return None
    
    def extract_numeric_value(self, text: str) -> Optional[float]:
        """
        Извлекает числовое значение из текста.
        
        Args:
            text: Текст для извлечения числа
            
        Returns:
            Числовое значение или None
        """
        if not text or not isinstance(text, str):
            return None
        
        # Ищем числа в тексте (включая десятичные)
        numbers = re.findall(r'\d+[.,]?\d*', text)
        if numbers:
            try:
                # Берем первое найденное число
                return float(numbers[0].replace(',', '.'))
            except ValueError:
                pass
        
        return None
    
    def extract_specifications_from_excel(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает спецификации из данных Excel.
        
        Args:
            excel_data: Данные из Excel
            
        Returns:
            Словарь со спецификациями
        """
        specs = {}
        
        # Ищем различные варианты названий колонок и значений
        for col, value in excel_data.items():
            if pd.isna(value) or not isinstance(value, str):
                continue
            
            value_lower = str(value).lower()
            
            # Мощность охлаждения
            if any(keyword in value_lower for keyword in ['мощность охлаждения', 'охлаждение', 'квт охлаждение']):
                numeric_value = self.extract_numeric_value(value)
                if numeric_value:
                    specs['cooling_power_kw'] = numeric_value
            
            # Мощность обогрева
            elif any(keyword in value_lower for keyword in ['мощность обогрева', 'обогрев', 'квт обогрев']):
                numeric_value = self.extract_numeric_value(value)
                if numeric_value:
                    specs['heating_power_kw'] = numeric_value
            
            # Потребление при охлаждении
            elif any(keyword in value_lower for keyword in ['потребление охлаждение', 'энергопотребление охлаждение']):
                numeric_value = self.extract_numeric_value(value)
                if numeric_value:
                    specs['cooling_consumption_kw'] = numeric_value
            
            # Потребление при обогреве
            elif any(keyword in value_lower for keyword in ['потребление обогрев', 'энергопотребление обогрев']):
                numeric_value = self.extract_numeric_value(value)
                if numeric_value:
                    specs['heating_consumption_kw'] = numeric_value
            
            # Диаметр труб
            elif any(keyword in value_lower for keyword in ['диаметр труб', 'трубы', 'диаметр']):
                specs['pipe_diameter'] = str(value)
            
            # Класс энергоэффективности
            elif any(keyword in value_lower for keyword in ['класс энергоэффективности', 'энергоэффективность', 'класс']):
                specs['energy_efficiency_class'] = str(value)
        
        return specs
    
    def extract_pricing_from_excel(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает информацию о ценах из данных Excel.
        
        Args:
            excel_data: Данные из Excel
            
        Returns:
            Словарь с ценами
        """
        pricing = {}
        
        for col, value in excel_data.items():
            if pd.isna(value):
                continue
            
            value_str = str(value).lower()
            
            # Ищем цены в USD
            if any(keyword in value_str for keyword in ['usd', '$', 'доллар']):
                numeric_value = self.extract_numeric_value(str(value))
                if numeric_value:
                    if 'опт' in value_str or 'дилер' in value_str:
                        pricing['dealer_price_usd'] = numeric_value
                    else:
                        pricing['retail_price_usd'] = numeric_value
            
            # Ищем цены в BYN
            elif any(keyword in value_str for keyword in ['byn', 'byr', 'бел.руб', 'руб']):
                numeric_value = self.extract_numeric_value(str(value))
                if numeric_value:
                    pricing['retail_price_byn'] = numeric_value
        
        return pricing
    
    def validate_and_update_aircon(self, aircon: Dict[str, Any]) -> bool:
        """
        Валидирует и обновляет данные кондиционера.
        
        Args:
            aircon: Данные кондиционера из JSON
            
        Returns:
            True если кондиционер найден и обновлен, False если удален
        """
        model_name = aircon.get('model_name', '')
        
        # Ищем модель в Excel
        excel_result = self.find_model_in_excel(model_name)
        
        if excel_result is None:
            logger.warning(f"Модель не найдена в Excel: {model_name}")
            self.stats['not_found'] += 1
            return False
        
        logger.info(f"Найдена модель в Excel: {model_name} ({excel_result['match_type']})")
        self.stats['found_in_excel'] += 1
        
        # Извлекаем данные из Excel
        excel_data = excel_result['data']
        
        # Обновляем спецификации
        new_specs = self.extract_specifications_from_excel(excel_data)
        if new_specs:
            aircon['specifications'].update(new_specs)
        
        # Обновляем цены
        new_pricing = self.extract_pricing_from_excel(excel_data)
        if new_pricing:
            aircon['pricing'].update(new_pricing)
        
        # Обновляем информацию о поставщике
        supplier_info = {
            'name': 'Excel Source',
            'source_file': excel_result['source_file'],
            'source_sheet': excel_result['source_sheet'],
            'dealer_price_usd': new_pricing.get('dealer_price_usd'),
            'retail_price_usd': new_pricing.get('retail_price_usd'),
            'retail_price_byn': new_pricing.get('retail_price_byn')
        }
        
        # Добавляем или обновляем информацию о поставщике
        aircon['suppliers'] = [supplier_info]
        
        # Обновляем время последнего обновления
        aircon['last_updated'] = datetime.now().isoformat()
        
        self.stats['updated'] += 1
        return True
    
    def validate_catalog(self) -> bool:
        """
        Валидирует весь каталог кондиционеров.
        
        Returns:
            True если валидация прошла успешно
        """
        logger.info("Начинаем валидацию каталога...")
        
        if not self.catalog_data or 'air_conditioners' not in self.catalog_data:
            logger.error("Некорректная структура JSON-каталога")
            return False
        
        # Фильтруем кондиционеры
        original_count = len(self.catalog_data['air_conditioners'])
        validated_aircons = []
        
        for aircon in self.catalog_data['air_conditioners']:
            if self.validate_and_update_aircon(aircon):
                validated_aircons.append(aircon)
            else:
                self.stats['removed'] += 1
        
        # Обновляем каталог
        self.catalog_data['air_conditioners'] = validated_aircons
        
        # Обновляем статистику каталога
        self.catalog_data['catalog_info']['total_models'] = len(validated_aircons)
        self.catalog_data['catalog_info']['last_updated'] = datetime.now().isoformat()
        self.catalog_data['catalog_info']['version'] = "2.0"
        
        logger.info(f"Валидация завершена:")
        logger.info(f"  Исходное количество: {original_count}")
        logger.info(f"  Найдено в Excel: {self.stats['found_in_excel']}")
        logger.info(f"  Обновлено: {self.stats['updated']}")
        logger.info(f"  Удалено: {self.stats['removed']}")
        logger.info(f"  Итоговое количество: {len(validated_aircons)}")
        
        return True
    
    def save_validated_catalog(self) -> bool:
        """
        Сохраняет валидированный каталог.
        
        Returns:
            True если сохранение прошло успешно
        """
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Валидированный каталог сохранен: {self.output_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения каталога: {e}")
            return False

def main():
    """Основная функция."""
    # Пути к файлам
    json_path = "docs/airs_catalog.json"
    excel_dir = "docs/prices_and_catalog"
    output_path = "docs/new_airs_catalog.json"
    
    # Создаем создателя валидного каталога
    creator = ValidAirCatalogCreator(json_path, excel_dir, output_path)
    
    # Загружаем существующий каталог
    if not creator.load_existing_catalog():
        logger.error("Не удалось загрузить существующий каталог")
        return
    
    # Загружаем Excel-файлы
    if not creator.load_excel_files():
        logger.error("Не удалось загрузить Excel-файлы")
        return
    
    # Валидируем каталог
    if not creator.validate_catalog():
        logger.error("Ошибка валидации каталога")
        return
    
    # Сохраняем результат
    if not creator.save_validated_catalog():
        logger.error("Не удалось сохранить валидированный каталог")
        return
    
    logger.info("Создание валидного каталога завершено успешно!")

if __name__ == "__main__":
    main() 