"""
Скрипт для создания нового JSON-каталога кондиционеров на основе Excel-файлов.

Алгоритм:
1. Загружаем все Excel-файлы из docs/prices_and_catalog
2. Извлекаем данные о кондиционерах из каждого файла
3. Нормализуем и структурируем данные
4. Создаем новый JSON-каталог с правильной структурой
5. Сохраняем как new_airs_catalog.json
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
        logging.FileHandler('create_new_airs_catalog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NewAirCatalogCreator:
    def __init__(self, excel_dir: str, output_path: str):
        """
        Инициализация создателя каталога.
        
        Args:
            excel_dir: Путь к папке с Excel-файлами
            output_path: Путь для сохранения нового JSON-каталога
        """
        self.excel_dir = excel_dir
        self.output_path = output_path
        self.excel_data = {}
        self.air_conditioners = []
        self.stats = {
            'total_files': 0,
            'total_sheets': 0,
            'total_models': 0,
            'processed_models': 0
        }
    
    def load_excel_files(self) -> bool:
        """Загружает все Excel-файлы в память."""
        try:
            excel_files = [f for f in os.listdir(self.excel_dir) if f.endswith('.xlsx')]
            logger.info(f"Найдено {len(excel_files)} Excel-файлов")
            self.stats['total_files'] = len(excel_files)
            
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
                                self.stats['total_sheets'] += 1
                                logger.info(f"  Загружен лист: {sheet_name} ({len(df)} строк)")
                        except Exception as e:
                            logger.warning(f"  Ошибка чтения листа {sheet_name}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Ошибка чтения файла {file_name}: {e}")
                    continue
            
            logger.info(f"Загружено {self.stats['total_sheets']} листов из Excel-файлов")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки Excel-файлов: {e}")
            return False
    
    def find_model_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        Ищет колонку с названиями моделей кондиционеров.
        
        Args:
            df: DataFrame для поиска
            
        Returns:
            Название колонки или None
        """
        model_keywords = ['модель', 'название', 'артикул', 'код', 'model', 'name', 'article']
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in model_keywords):
                return col
        
        # Если не нашли по ключевым словам, ищем колонку с данными, похожими на модели
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                # Проверяем, есть ли в колонке данные, похожие на модели кондиционеров
                sample_values = df[col].dropna().head(10)
                if len(sample_values) > 0:
                    # Ищем паттерны, характерные для моделей кондиционеров
                    model_patterns = [r'[A-Z]{2,}-\d+', r'[A-Z]{2,}\d+', r'[A-Z]{2,}/\d+']
                    for pattern in model_patterns:
                        matches = sample_values.astype(str).str.contains(pattern, regex=True)
                        if matches.any() and matches.sum() > len(sample_values) * 0.3:
                            return col
        
        return None
    
    def find_price_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Ищет колонки с ценами.
        
        Args:
            df: DataFrame для поиска
            
        Returns:
            Словарь {тип_цены: название_колонки}
        """
        price_columns = {}
        
        price_patterns = {
            'dealer_price_usd': ['опт', 'дилер', 'usd', '$', 'оптовая'],
            'retail_price_usd': ['розница', 'retail', 'usd', '$', 'розничная'],
            'retail_price_byn': ['byr', 'byn', 'бел.руб', 'руб', 'белорусские рубли']
        }
        
        for price_type, keywords in price_patterns.items():
            for col in df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in keywords):
                    price_columns[price_type] = col
                    break
        
        return price_columns
    
    def find_specification_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Ищет колонки со спецификациями.
        
        Args:
            df: DataFrame для поиска
            
        Returns:
            Словарь {спецификация: название_колонки}
        """
        spec_columns = {}
        
        spec_patterns = {
            'cooling_power_kw': ['мощность охлаждения', 'охлаждение', 'квт охлаждение', 'мощность'],
            'heating_power_kw': ['мощность обогрева', 'обогрев', 'мощность обогрева'],
            'cooling_consumption_kw': ['потребление охлаждение', 'энергопотребление охлаждение'],
            'heating_consumption_kw': ['потребление обогрев', 'энергопотребление обогрев'],
            'pipe_diameter': ['диаметр труб', 'трубы', 'диаметр'],
            'energy_efficiency_class': ['класс энергоэффективности', 'энергоэффективность', 'класс']
        }
        
        for spec_type, keywords in spec_patterns.items():
            for col in df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in keywords):
                    spec_columns[spec_type] = col
                    break
        
        return spec_columns
    
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
    
    def normalize_model_name(self, model_name: str) -> str:
        """
        Нормализует название модели.
        
        Args:
            model_name: Исходное название модели
            
        Returns:
            Нормализованное название
        """
        if not model_name:
            return ""
        
        # Приводим к верхнему регистру и убираем лишние пробелы
        normalized = str(model_name).upper().strip()
        
        # Убираем лишние символы
        normalized = re.sub(r'[^\w\s\-/]', '', normalized)
        
        # Заменяем множественные пробелы на один
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def extract_brand_from_model(self, model_name: str) -> str:
        """
        Извлекает бренд из названия модели.
        
        Args:
            model_name: Название модели
            
        Returns:
            Бренд
        """
        if not model_name:
            return "Unknown"
        
        # Известные бренды
        known_brands = ['DANTEX', 'MITSUBISHI', 'TCL', 'ASPEN', 'REFCO', 'VARIOUS']
        
        model_upper = model_name.upper()
        for brand in known_brands:
            if brand in model_upper:
                return brand
        
        # Если не нашли известный бренд, пытаемся извлечь из начала названия
        parts = model_name.split('-')
        if len(parts) > 0:
            potential_brand = parts[0].strip()
            if len(potential_brand) >= 2:
                return potential_brand
        
        return "Unknown"
    
    def process_dataframe(self, df: pd.DataFrame, source_file: str, source_sheet: str) -> List[Dict[str, Any]]:
        """
        Обрабатывает DataFrame и извлекает данные о кондиционерах.
        
        Args:
            df: DataFrame для обработки
            source_file: Имя исходного файла
            source_sheet: Имя листа
            
        Returns:
            Список словарей с данными кондиционеров
        """
        air_conditioners = []
        
        # Ищем колонку с моделями
        model_col = self.find_model_column(df)
        if not model_col:
            logger.warning(f"Не найдена колонка с моделями в {source_file}/{source_sheet}")
            return air_conditioners
        
        # Ищем колонки с ценами
        price_cols = self.find_price_columns(df)
        
        # Ищем колонки со спецификациями
        spec_cols = self.find_specification_columns(df)
        
        logger.info(f"Обрабатываем {source_file}/{source_sheet}:")
        logger.info(f"  Колонка моделей: {model_col}")
        logger.info(f"  Колонки цен: {list(price_cols.keys())}")
        logger.info(f"  Колонки спецификаций: {list(spec_cols.keys())}")
        
        # Обрабатываем каждую строку
        for idx, row in df.iterrows():
            model_name = row.get(model_col)
            if not model_name or pd.isna(model_name):
                continue
            
            normalized_model = self.normalize_model_name(model_name)
            if not normalized_model:
                continue
            
            # Создаем запись кондиционера
            aircon = {
                'model_name': normalized_model,
                'brand': self.extract_brand_from_model(normalized_model),
                'series': '',
                'specifications': {},
                'pricing': {},
                'suppliers': [],
                'description': '',
                'pdf_source': '',
                'representative_image': '',
                'available_images_count': 0,
                'last_updated': datetime.now().isoformat(),
                'air_description': ''
            }
            
            # Извлекаем спецификации
            for spec_type, col in spec_cols.items():
                value = row.get(col)
                if value and not pd.isna(value):
                    numeric_value = self.extract_numeric_value(str(value))
                    if numeric_value is not None:
                        aircon['specifications'][spec_type] = numeric_value
            
            # Извлекаем цены
            for price_type, col in price_cols.items():
                value = row.get(col)
                if value and not pd.isna(value):
                    numeric_value = self.extract_numeric_value(str(value))
                    if numeric_value is not None:
                        aircon['pricing'][price_type] = numeric_value
            
            # Добавляем информацию о поставщике
            supplier_info = {
                'name': 'Excel Source',
                'source_file': source_file,
                'source_sheet': source_sheet
            }
            
            # Копируем цены в информацию о поставщике
            for price_type, value in aircon['pricing'].items():
                supplier_info[price_type] = value
            
            aircon['suppliers'].append(supplier_info)
            
            # Создаем описание
            description_parts = []
            if aircon['specifications'].get('cooling_power_kw'):
                description_parts.append(f"Мощность охлаждения: {aircon['specifications']['cooling_power_kw']} кВт")
            if aircon['specifications'].get('heating_power_kw'):
                description_parts.append(f"Мощность обогрева: {aircon['specifications']['heating_power_kw']} кВт")
            
            if description_parts:
                aircon['air_description'] = f"Кондиционер {aircon['brand']} {aircon['model_name']} — {' '.join(description_parts)}"
            
            air_conditioners.append(aircon)
            self.stats['processed_models'] += 1
        
        return air_conditioners
    
    def create_catalog(self) -> bool:
        """
        Создает новый каталог кондиционеров.
        
        Returns:
            True если создание прошло успешно
        """
        logger.info("Начинаем создание нового каталога...")
        
        # Обрабатываем все Excel-данные
        for key, df in self.excel_data.items():
            source_file = df['_source_file'].iloc[0]
            source_sheet = df['_source_sheet'].iloc[0]
            
            air_conditioners = self.process_dataframe(df, source_file, source_sheet)
            self.air_conditioners.extend(air_conditioners)
        
        # Удаляем дубликаты по model_name
        unique_models = {}
        for aircon in self.air_conditioners:
            model_name = aircon['model_name']
            if model_name not in unique_models:
                unique_models[model_name] = aircon
            else:
                # Объединяем информацию о поставщиках
                unique_models[model_name]['suppliers'].extend(aircon['suppliers'])
        
        self.air_conditioners = list(unique_models.values())
        self.stats['total_models'] = len(self.air_conditioners)
        
        logger.info(f"Создан каталог с {self.stats['total_models']} уникальными моделями")
        return True
    
    def create_catalog_structure(self) -> Dict[str, Any]:
        """
        Создает структуру каталога.
        
        Returns:
            Словарь с структурой каталога
        """
        return {
            "catalog_info": {
                "name": "Новый каталог кондиционеров",
                "description": "Каталог кондиционеров, созданный на основе Excel-файлов поставщиков",
                "total_models": self.stats['total_models'],
                "generated_at": datetime.now().isoformat(),
                "sources": {
                    "xlsx_files_processed": self.stats['total_files'],
                    "total_sheets_processed": self.stats['total_sheets'],
                    "models_processed": self.stats['processed_models']
                },
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
                "features": [
                    "Данные из Excel-файлов поставщиков",
                    "Валидированные модели кондиционеров",
                    "Актуальные цены и спецификации",
                    "Информация о поставщиках"
                ]
            },
            "air_conditioners": self.air_conditioners
        }
    
    def save_catalog(self) -> bool:
        """
        Сохраняет каталог в JSON-файл.
        
        Returns:
            True если сохранение прошло успешно
        """
        try:
            catalog_structure = self.create_catalog_structure()
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(catalog_structure, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Каталог сохранен: {self.output_path}")
            logger.info(f"Статистика:")
            logger.info(f"  Обработано файлов: {self.stats['total_files']}")
            logger.info(f"  Обработано листов: {self.stats['total_sheets']}")
            logger.info(f"  Найдено моделей: {self.stats['processed_models']}")
            logger.info(f"  Уникальных моделей: {self.stats['total_models']}")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения каталога: {e}")
            return False

def main():
    """Основная функция."""
    # Пути к файлам
    excel_dir = "docs/prices_and_catalog"
    output_path = "docs/new_airs_catalog.json"
    
    # Создаем создателя каталога
    creator = NewAirCatalogCreator(excel_dir, output_path)
    
    # Загружаем Excel-файлы
    if not creator.load_excel_files():
        logger.error("Не удалось загрузить Excel-файлы")
        return
    
    # Создаем каталог
    if not creator.create_catalog():
        logger.error("Ошибка создания каталога")
        return
    
    # Сохраняем результат
    if not creator.save_catalog():
        logger.error("Не удалось сохранить каталог")
        return
    
    logger.info("Создание нового каталога завершено успешно!")

if __name__ == "__main__":
    main() 