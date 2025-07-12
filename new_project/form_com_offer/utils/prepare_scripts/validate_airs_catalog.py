"""
Скрипт для валидации airs_catalog.json по данным из Excel-файлов.

Алгоритм:
1. Загружаем JSON с кондиционерами
2. Для каждого кондиционера ищем его в Excel-файлах по model_name
3. Если не находим — удаляем из JSON
4. Если находим — сверяем все поля и обновляем данные в JSON
5. Сохраняем очищенный и валидированный JSON
"""
import json
import pandas as pd
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Any
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validate_airs_catalog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AirConditionerValidator:
    def __init__(self, json_path: str, excel_dir: str):
        """
        Инициализация валидатора.
        
        Args:
            json_path: Путь к JSON-файлу с кондиционерами
            excel_dir: Путь к папке с Excel-файлами
        """
        self.json_path = json_path
        self.excel_dir = excel_dir
        self.catalog_data = None
        self.excel_data = {}
        self.validation_stats = {
            'total_models': 0,
            'found_in_excel': 0,
            'not_found': 0,
            'updated': 0,
            'removed': 0
        }
    
    def load_json_catalog(self) -> bool:
        """Загружает JSON-каталог кондиционеров."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.catalog_data = json.load(f)
            logger.info(f"Загружен JSON-каталог с {len(self.catalog_data['air_conditioners'])} кондиционерами")
            self.validation_stats['total_models'] = len(self.catalog_data['air_conditioners'])
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
        normalized = model_name.upper().strip()
        
        # Убираем лишние символы
        normalized = re.sub(r'[^\w\s\-/]', '', normalized)
        
        # Заменяем множественные пробелы на один
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def find_model_in_excel(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Ищет модель в Excel-данных.
        
        Args:
            model_name: Название модели для поиска
            
        Returns:
            Словарь с найденными данными или None
        """
        normalized_search = self.normalize_model_name(model_name)
        
        if not normalized_search:
            return None
        
        for key, df in self.excel_data.items():
            # Ищем в разных колонках (могут быть разные названия колонок)
            for col in df.columns:
                if pd.api.types.is_string_dtype(df[col]):
                    # Нормализуем значения в колонке для поиска
                    normalized_values = df[col].astype(str).apply(self.normalize_model_name)
                    
                    # Ищем точное совпадение
                    matches = normalized_values == normalized_search
                    if matches.any():
                        row = df[matches].iloc[0]
                        return {
                            'data': row.to_dict(),
                            'source_file': row.get('_source_file', ''),
                            'source_sheet': row.get('_source_sheet', ''),
                            'excel_key': key
                        }
                    
                    # Ищем частичное совпадение
                    partial_matches = normalized_values.str.contains(normalized_search, na=False)
                    if partial_matches.any():
                        row = df[partial_matches].iloc[0]
                        return {
                            'data': row.to_dict(),
                            'source_file': row.get('_source_file', ''),
                            'source_sheet': row.get('_source_sheet', ''),
                            'excel_key': key
                        }
        
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
        
        # Ищем различные варианты названий колонок
        power_patterns = {
            'cooling_power': ['мощность охлаждения', 'охлаждение', 'мощность', 'квт охлаждение'],
            'heating_power': ['мощность обогрева', 'обогрев', 'мощность обогрева'],
            'cooling_consumption': ['потребление охлаждение', 'энергопотребление охлаждение'],
            'heating_consumption': ['потребление обогрев', 'энергопотребление обогрев'],
            'pipe_diameter': ['диаметр труб', 'трубы', 'диаметр'],
            'energy_efficiency': ['класс энергоэффективности', 'энергоэффективность', 'класс']
        }
        
        for spec_key, patterns in power_patterns.items():
            for pattern in patterns:
                for col, value in excel_data.items():
                    if isinstance(value, str) and pattern.lower() in value.lower():
                        # Пытаемся извлечь числовое значение
                        numeric_value = self.extract_numeric_value(value)
                        if numeric_value is not None:
                            specs[spec_key] = numeric_value
                            break
        
        return specs
    
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
        
        # Ищем числа в тексте
        numbers = re.findall(r'\d+[.,]?\d*', text)
        if numbers:
            try:
                # Берем первое найденное число
                return float(numbers[0].replace(',', '.'))
            except ValueError:
                pass
        
        return None
    
    def extract_pricing_from_excel(self, excel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает информацию о ценах из данных Excel.
        
        Args:
            excel_data: Данные из Excel
            
        Returns:
            Словарь с ценами
        """
        pricing = {}
        
        price_patterns = {
            'dealer_price_usd': ['опт', 'дилер', 'usd', '$'],
            'retail_price_usd': ['розница', 'retail', 'usd', '$'],
            'retail_price_byn': ['byr', 'byn', 'бел.руб', 'руб']
        }
        
        for price_key, patterns in price_patterns.items():
            for pattern in patterns:
                for col, value in excel_data.items():
                    if isinstance(value, str) and pattern.lower() in value.lower():
                        numeric_value = self.extract_numeric_value(value)
                        if numeric_value is not None:
                            pricing[price_key] = numeric_value
                            break
        
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
            self.validation_stats['not_found'] += 1
            return False
        
        logger.info(f"Найдена модель в Excel: {model_name}")
        self.validation_stats['found_in_excel'] += 1
        
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
        
        self.validation_stats['updated'] += 1
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
                self.validation_stats['removed'] += 1
        
        # Обновляем каталог
        self.catalog_data['air_conditioners'] = validated_aircons
        
        # Обновляем статистику каталога
        self.catalog_data['catalog_info']['total_models'] = len(validated_aircons)
        self.catalog_data['catalog_info']['last_updated'] = pd.Timestamp.now().isoformat()
        
        logger.info(f"Валидация завершена:")
        logger.info(f"  Исходное количество: {original_count}")
        logger.info(f"  Найдено в Excel: {self.validation_stats['found_in_excel']}")
        logger.info(f"  Обновлено: {self.validation_stats['updated']}")
        logger.info(f"  Удалено: {self.validation_stats['removed']}")
        logger.info(f"  Итоговое количество: {len(validated_aircons)}")
        
        return True
    
    def save_validated_catalog(self, output_path: str) -> bool:
        """
        Сохраняет валидированный каталог.
        
        Args:
            output_path: Путь для сохранения
            
        Returns:
            True если сохранение прошло успешно
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Валидированный каталог сохранен: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения каталога: {e}")
            return False

def main():
    """Основная функция."""
    # Пути к файлам
    json_path = "docs/airs_catalog.json"
    excel_dir = "docs/prices_and_catalog"
    output_path = "docs/airs_catalog_validated.json"
    
    # Создаем валидатор
    validator = AirConditionerValidator(json_path, excel_dir)
    
    # Загружаем данные
    if not validator.load_json_catalog():
        logger.error("Не удалось загрузить JSON-каталог")
        return
    
    if not validator.load_excel_files():
        logger.error("Не удалось загрузить Excel-файлы")
        return
    
    # Валидируем каталог
    if not validator.validate_catalog():
        logger.error("Ошибка валидации каталога")
        return
    
    # Сохраняем результат
    if not validator.save_validated_catalog(output_path):
        logger.error("Не удалось сохранить валидированный каталог")
        return
    
    logger.info("Валидация завершена успешно!")

if __name__ == "__main__":
    main() 