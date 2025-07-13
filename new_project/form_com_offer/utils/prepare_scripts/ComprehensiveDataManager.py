# -*- coding: utf-8 -*-
"""
Этот модуль содержит единый класс ComprehensiveDataManager, предназначенный для комплексной
обработки данных, связанных с каталогами климатического оборудования и комплектующих.
Он объединяет, улучшает и унифицирует логику из множества разрозненных скриптов.
"""

import os
import json
import re
import math
import shutil
import zipfile
import io
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Сторонние библиотеки (необходимо установить: pip install pandas openpyxl Pillow PyMuPDF)
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
import numpy as np

# Кастомный логгер, как и было указано в задании.
# Предполагается, что файл mylogger.py находится в папке utils.
# Если это не так, нужно будет скорректировать импорт или предоставить код логгера.
# Пример реализации логгера будет приведен в блоке `if __name__ == "__main__"`.
try:
    from utils.mylogger import Logger
except ImportError:
    # Заглушка, если кастомный логгер не найден. Это позволит коду не падать.
    import logging
    class Logger:
        def __init__(self, name, log_file):
            self.logger = logging.getLogger(name)
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            if not self.logger.handlers:
                self.logger.addHandler(handler)
        def info(self, msg): self.logger.info(msg)
        def warning(self, msg): self.logger.warning(msg)
        def error(self, msg): self.logger.error(msg)
        def debug(self, msg): self.logger.debug(msg)
        def exception(self, msg): self.logger.exception(msg)


class ComprehensiveDataManager:
    """
    Класс для комплексного управления данными каталогов оборудования и комплектующих.

    Этот класс инкапсулирует полный цикл работы с данными:
    - Извлечение данных из различных источников (Excel, PDF).
    - Извлечение изображений из файлов.
    - Создание, обновление и валидация JSON-каталогов для кондиционеров и комплектующих.
    - Нормализация, очистка и обогащение данных.
    - Генерация описаний на основе извлеченной информации.
    - Создание изображений-заглушек для компонентов.
    - Предоставление утилит для управления записями в каталогах.
    """
    def __init__(self, base_path: str = 'docs'):
        """
        Инициализирует менеджер данных.

        Args:
            base_path (str): Корневой путь к папке с данными ('docs').
        """
        self.class_name = self.__class__.__name__
        self.logger = Logger(name=self.class_name, log_file=f"{self.class_name.lower()}.log")
        
        # --- Основные пути ---
        self.base_path = base_path
        self.json_path = os.path.join(base_path, 'JSON_files')
        self.images_comp_path = os.path.join(base_path, 'images_comp')
        self.images_air_path = os.path.join(base_path, 'images')
        self.excel_path = os.path.join(base_path, 'prices_air_and_complectations')
        self.pdf_path = os.path.join(base_path, 'air_catalogs')

        # --- Пути к ключевым файлам каталогов ---
        self.components_catalog_path = os.path.join(self.json_path, 'components_catalog.json')
        self.air_conditioner_catalog_path = os.path.join(self.json_path, 'complete_air_conditioners_catalog.json')
        
        # --- Внутренний кэш для загруженных данных ---
        self._excel_data_cache: Dict[str, pd.DataFrame] = {}

        self.logger.info(f"'{self.class_name}' инициализирован. Base path: '{self.base_path}'")
        self._ensure_directories_exist()

    def _ensure_directories_exist(self):
        """Проверяет и создает необходимые директории, если они отсутствуют."""
        paths_to_check = [
            self.json_path,
            self.images_comp_path,
            self.images_air_path,
            self.excel_path,
            self.pdf_path
        ]
        for path in paths_to_check:
            if not os.path.exists(path):
                os.makedirs(path)
                self.logger.info(f"Создана директория: {path}")

    # ==========================================================================
    # 1. НИЗКОУРОВНЕВЫЕ УТИЛИТЫ (ЗАГРУЗКА/СОХРАНЕНИЕ, НОРМАЛИЗАЦИЯ)
    # ==========================================================================

    def _load_json(self, file_path: str, fix_nan: bool = True) -> Optional[Dict[str, Any]]:
        """
        Безопасно загружает JSON-файл с возможностью исправления 'NaN'.

        Args:
            file_path (str): Путь к JSON-файлу.
            fix_nan (bool): Если True, заменяет 'NaN' на 'null' перед парсингом.

        Returns:
            Optional[Dict[str, Any]]: Загруженные данные в виде словаря или None в случае ошибки.
        """
        if not os.path.exists(file_path):
            self.logger.warning(f"Файл не найден: {file_path}")
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if fix_nan:
                # NaN не является валидным JSON, заменяем его на null (None в Python)
                if 'NaN' in content:
                    self.logger.debug(f"Обнаружен NaN в файле {file_path}, выполняется замена на null.")
                    content = content.replace('NaN', 'null')

            data = json.loads(content)
            self.logger.info(f"Успешно загружен JSON из файла: {file_path}")
            return data
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка декодирования JSON в файле {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.exception(f"Непредвиденная ошибка при загрузке JSON из {file_path}: {e}")
            return None

    @staticmethod
    def _custom_json_serializer(obj: Any) -> Any:
        """
        Кастомный сериализатор для обработки специфичных типов данных (numpy, pandas) при сохранении в JSON.
        """
        if isinstance(obj, (datetime, pd.Timestamp, np.datetime64)):
            return obj.isoformat()
        if isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.float64, np.float32)):
            return float(obj) if not pd.isna(obj) else None
        if pd.isna(obj):
            return None
        raise TypeError(f"Объект типа {obj.__class__.__name__} не является JSON-сериализуемым")

    def _save_json(self, data: Dict, file_path: str, create_backup: bool = True):
        """
        Безопасно сохраняет данные в JSON-файл.

        Args:
            data (Dict): Данные для сохранения.
            file_path (str): Путь для сохранения файла.
            create_backup (bool): Создавать ли резервную копию перед сохранением.
        """
        try:
            # Рекурсивная очистка данных от не-JSON-совместимых значений
            sanitized_data = self._sanitize_json_data(data)

            if create_backup and os.path.exists(file_path):
                backup_path = file_path + '.backup'
                shutil.copy2(file_path, backup_path)
                self.logger.info(f"Создана резервная копия: {backup_path}")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sanitized_data, f, ensure_ascii=False, indent=2, default=self._custom_json_serializer)
            self.logger.info(f"Данные успешно сохранены в файл: {file_path}")
        except Exception as e:
            self.logger.exception(f"Ошибка при сохранении JSON в файл {file_path}: {e}")
            
    def _sanitize_json_data(self, data: Any) -> Any:
        """
        Рекурсивно очищает данные, заменяя NaN, inf и другие не-JSON значения на None.

        Args:
            data (Any): Входные данные (словарь, список и т.д.).

        Returns:
            Any: Очищенные данные.
        """
        if isinstance(data, dict):
            return {k: self._sanitize_json_data(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        if isinstance(data, float):
            if math.isnan(data) or math.isinf(data):
                return None
        if isinstance(data, str) and data in ('NaN', 'nan', 'inf', '-inf'):
            return None
        return data

    @staticmethod
    def _normalize_model_name(model_name: str) -> str:
        """
        Нормализует название модели для сопоставления (убирает лишние символы, приводит к верхнему регистру).

        Args:
            model_name (str): Исходное название модели.

        Returns:
            str: Нормализованное название.
        """
        if not model_name or pd.isna(model_name):
            return ""
        normalized = str(model_name).upper().strip()
        normalized = re.sub(r'[^\w\s\-/]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    @staticmethod
    def _extract_numeric_value(text: Any) -> Optional[float]:
        """
        Извлекает первое числовое значение из строки.

        Args:
            text (Any): Текст для извлечения числа.

        Returns:
            Optional[float]: Числовое значение или None.
        """
        if not text or pd.isna(text):
            return None
        # Ищем числа, включая десятичные с точкой или запятой
        numbers = re.findall(r'(\d+[.,]?\d*)', str(text))
        if numbers:
            try:
                return float(numbers[0].replace(',', '.'))
            except (ValueError, IndexError):
                return None
        return None

    # ==========================================================================
    # 2. ИЗВЛЕЧЕНИЕ ДАННЫХ ИЗ ИСТОЧНИКОВ (EXCEL, PDF)
    # ==========================================================================

    def _extract_data_from_xlsx(self, directory: str) -> List[Dict]:
        """
        Извлекает все данные со всех листов всех XLSX файлов в указанной директории.

        Args:
            directory (str): Путь к директории с Excel-файлами.

        Returns:
            List[Dict]: Список словарей, где каждый словарь - строка из Excel.
        """
        self.logger.info(f"Начинаю извлечение данных из Excel-файлов в директории: {directory}")
        all_data = []
        if not os.path.exists(directory):
            self.logger.warning(f"Директория не найдена: {directory}")
            return []

        for filename in os.listdir(directory):
            if filename.endswith('.xlsx') and not filename.startswith('~$'):
                file_path = os.path.join(directory, filename)
                self.logger.debug(f"Обработка файла: {file_path}")
                try:
                    excel_file = pd.ExcelFile(file_path)
                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(excel_file, sheet_name=sheet_name)
                        # Добавляем информацию об источнике
                        df['_source_file'] = filename
                        df['_source_sheet'] = sheet_name
                        # Конвертируем в список словарей и добавляем к общему списку
                        all_data.extend(df.to_dict(orient='records'))
                except Exception as e:
                    self.logger.error(f"Ошибка при чтении файла {filename}: {e}")
        
        self.logger.info(f"Извлечено {len(all_data)} записей из {len(os.listdir(directory))} файлов.")
        return all_data

    def _extract_data_from_pdfs(self, directory: str) -> List[Dict]:
        """
        Извлекает текст и изображения из всех PDF файлов в директории.

        Args:
            directory (str): Путь к директории с PDF-файлами.

        Returns:
            List[Dict]: Список словарей, где каждый словарь - данные одного PDF.
        """
        self.logger.info(f"Начинаю извлечение данных из PDF-файлов в директории: {directory}")
        all_pdf_data = []
        if not os.path.exists(directory):
            self.logger.warning(f"Директория не найдена: {directory}")
            return []

        for filename in os.listdir(directory):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(directory, filename)
                self.logger.debug(f"Обработка PDF-файла: {file_path}")
                try:
                    doc = fitz.open(file_path)
                    pdf_data = {
                        'file_name': filename,
                        'text_content': "",
                        'images': []
                    }
                    image_counter = 0
                    for page_num, page in enumerate(doc):
                        pdf_data['text_content'] += f"\n--- Page {page_num + 1} ---\n{page.get_text()}"
                        for img_index, img in enumerate(page.get_images(full=True)):
                            xref = img[0]
                            pix = fitz.Pixmap(doc, xref)
                            # Пропускаем маленькие и не-RGB/Grayscale изображения
                            if pix.n < 5 and pix.width > 50 and pix.height > 50:
                                img_filename = f"{os.path.splitext(filename)[0]}_page{page_num+1}_img{img_index}.png"
                                img_path = os.path.join(self.images_air_path, img_filename)
                                pix.save(img_path)
                                pdf_data['images'].append({
                                    'filename': img_filename,
                                    'path': img_path,
                                    'page': page_num + 1
                                })
                                image_counter += 1
                            pix = None  # Освобождаем память
                    doc.close()
                    all_pdf_data.append(pdf_data)
                    self.logger.debug(f"Извлечено {image_counter} изображений из {filename}")
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке PDF {filename}: {e}")

        self.logger.info(f"Обработано {len(all_pdf_data)} PDF-файлов.")
        return all_pdf_data

    def extract_images_from_xlsx_zip(self, excel_path: str, output_dir: str) -> Dict:
        """
        Извлекает все изображения из XLSX файла, используя его как ZIP-архив.

        Args:
            excel_path (str): Путь к Excel-файлу.
            output_dir (str): Папка для сохранения изображений.

        Returns:
            Dict: Словарь с информацией об извлеченных изображениях.
        """
        self.logger.info(f"Извлечение изображений из {excel_path} (метод ZIP)")
        if not os.path.exists(excel_path):
            self.logger.error(f"Excel-файл не найден: {excel_path}")
            return {}

        extracted_images = {}
        try:
            with zipfile.ZipFile(excel_path, 'r') as zf:
                media_files = [f for f in zf.namelist() if f.startswith('xl/media/')]
                self.logger.info(f"Найдено {len(media_files)} медиафайлов в архиве.")

                for i, media_file in enumerate(media_files):
                    with zf.open(media_file) as img_file:
                        img_data = img_file.read()
                        pil_img = Image.open(io.BytesIO(img_data))
                        
                        # Генерируем унифицированное имя файла
                        image_name = f"extracted_img_{os.path.splitext(os.path.basename(excel_path))[0]}_{i+1}.jpg"
                        output_path = os.path.join(output_dir, image_name)
                        
                        # Конвертируем в RGB для сохранения в JPEG
                        if pil_img.mode in ('RGBA', 'P', 'LA'):
                            pil_img = pil_img.convert('RGB')
                        
                        pil_img.save(output_path, 'JPEG', quality=90)
                        
                        extracted_images[image_name] = {
                            'original_name': media_file,
                            'path': output_path,
                            'size': pil_img.size
                        }
                        self.logger.debug(f"Сохранено изображение: {output_path}")
        except Exception as e:
            self.logger.exception(f"Ошибка при извлечении изображений из {excel_path}: {e}")

        self.logger.info(f"Всего извлечено {len(extracted_images)} изображений.")
        return extracted_images

    # ==========================================================================
    # 3. ЛОГИКА ДЛЯ КАТАЛОГА КОМПЛЕКТУЮЩИХ
    # ==========================================================================

    def create_initial_components_catalog(self, overwrite: bool = False):
        """
        Создает первоначальный JSON-каталог комплектующих из жестко заданных данных.
        
        Args:
            overwrite (bool): Если True, перезапишет существующий файл.
        """
        if os.path.exists(self.components_catalog_path) and not overwrite:
            self.logger.warning(f"Файл каталога {self.components_catalog_path} уже существует. Используйте `overwrite=True` для перезаписи.")
            return

        self.logger.info("Создание первоначального каталога комплектующих...")
        # Данные из скрипта create_components_catalog.py
        components_data = {
            "воздуховод 500х800": ("500x800 мм", "оцинкованная сталь", "класс герметичности А", 5000, "ГОСТ 14918-80"),
            "воздуховод d450": ("ø450 мм", "оцинкованная сталь", "класс герметичности А", 2500, "ГОСТ 14918-80"),
            "поворот 90° 500х800": ("500x800 мм", "оцинкованная сталь", "угол 90°", 1200, None),
            # ... (здесь должны быть все остальные данные)
        }
        
        components_list = []
        for i, (name, (size, material, chars, price, standard)) in enumerate(components_data.items()):
            category_display, category_folder = self._determine_component_category(name)
            component = {
                "id": i + 1, "name": name, "category": category_display,
                "size": size, "material": material, "characteristics": chars,
                "price": price, "currency": "BYN", "standard": standard,
                "manufacturer": None, "in_stock": True,
                "description": f"{name}, размер: {size}, материал: {material}",
                "image_path": None, "image_url": None,
                "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()
            }
            components_list.append(component)
            
        catalog_structure = {
            "catalog_info": {
                "name": "Каталог комплектующих для систем вентиляции",
                "version": "1.0", "total_components": len(components_list),
                "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()
            },
            "categories": sorted(list(set(c['category'] for c in components_list))),
            "components": components_list
        }
        self._save_json(catalog_structure, self.components_catalog_path)

    def _determine_component_category(self, component_name: str) -> Tuple[str, str]:
        """Определяет категорию компонента по его названию."""
        name_lower = component_name.lower()
        cat_map = {
            "воздуховоды": ("Воздуховоды", ["воздуховод"]),
            "отводы_повороты": ("Отводы и повороты", ["поворот", "отвод"]),
            "переходы": ("Переходы", ["переход"]),
            "тройники": ("Тройники", ["тройник"]),
            "врезки": ("Врезки", ["врезка"]),
            "насадки": ("Насадки", ["насадок"]),
            "клапаны": ("Клапаны", ["клапан", "дроссель"]),
            "оборудование": ("Оборудование", ["агрегат", "установка"]),
            "материалы": ("Материалы", ["сталь", "мат"]),
            "соединительные_элементы": ("Соединительные элементы", ["ниппель", "муфта", "заглушка"]),
            "регулирующие_элементы": ("Регулирующие элементы", ["зонт", "дефлектор"]),
            "гибкие_соединения": ("Гибкие соединения", ["гибкие"]),
        }
        for folder, (display, keywords) in cat_map.items():
            if any(kw in name_lower for kw in keywords):
                return display, folder
        return "Прочие комплектующие", "прочие"

    def generate_component_image_placeholders(self, overwrite: bool = False):
        """
        Создает изображения-заглушки для всех компонентов в каталоге.

        Args:
            overwrite (bool): Если True, перезапишет существующие изображения.
        """
        self.logger.info("Генерация изображений-заглушек для компонентов...")
        catalog = self._load_json(self.components_catalog_path)
        if not catalog or 'components' not in catalog:
            self.logger.error("Каталог компонентов не загружен или пуст.")
            return

        created_count, skipped_count, error_count = 0, 0, 0
        for component in catalog['components']:
            # Формируем имя файла изображения из имени компонента
            safe_filename = re.sub(r'[^\w\d-]', '_', component['name']) + '.jpg'
            image_path = os.path.join(self.images_comp_path, safe_filename)

            if os.path.exists(image_path) and not overwrite:
                skipped_count += 1
                continue
            
            try:
                self._create_placeholder_image(component, image_path)
                created_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка создания заглушки для '{component['name']}': {e}")
                error_count += 1
        
        self.logger.info(
            f"Генерация заглушек завершена. "
            f"Создано: {created_count}, Пропущено: {skipped_count}, Ошибок: {error_count}"
        )

    def _create_placeholder_image(self, component: Dict, output_path: str, image_size: Tuple[int, int] = (400, 300)):
        """
        Создает одно изображение-заглушку.

        Args:
            component (Dict): Данные компонента.
            output_path (str): Путь для сохранения изображения.
            image_size (Tuple[int, int]): Размер изображения.
        """
        img = Image.new('RGB', image_size, color=(245, 245, 245))
        draw = ImageDraw.Draw(img)
        
        category_colors = {
            'Воздуховоды': '#4CAF50', 'Отводы и повороты': '#2196F3', 'Переходы': '#FF9800',
            'Тройники': '#9C27B0', 'Врезки': '#F44336', 'Насадки': '#00BCD4',
            'Клапаны': '#795548', 'Оборудование': '#607D8B', 'Материалы': '#8BC34A',
            'Соединительные элементы': '#FFE0B2', 'Регулирующие элементы': '#E91E63',
        }
        category_color = category_colors.get(component.get('category', 'прочие'), '#757575')
        
        # Шапка с цветом категории
        draw.rectangle([0, 0, image_size[0], 50], fill=category_color)
        
        # Шрифты
        try:
            font_l = ImageFont.truetype("arial.ttf", 20)
            font_m = ImageFont.truetype("arial.ttf", 16)
            font_s = ImageFont.truetype("arial.ttf", 14)
        except IOError:
            font_l = font_m = font_s = ImageFont.load_default()

        # Текст
        y_offset = 15
        title = component.get('name', 'Без названия')
        draw.text((10, y_offset), title, fill='white', font=font_l)
        
        y_offset = 70
        info_lines = [
            f"Категория: {component.get('category', 'н/д')}",
            f"Размер: {component.get('size', 'н/д')}",
            f"Материал: {component.get('material', 'н/д')}",
            f"Цена: {component.get('price', '0')} {component.get('currency', 'BYN')}"
        ]
        
        for line in info_lines:
            if line:
                draw.text((20, y_offset), line, fill='black', font=font_m)
                y_offset += 25

        img.save(output_path, 'JPEG', quality=85)
        self.logger.debug(f"Изображение-заглушка создано: {output_path}")

    # ==========================================================================
    # 4. ЛОГИКА ДЛЯ КАТАЛОГА КОНДИЦИОНЕРОВ
    # ==========================================================================
    
    def create_full_air_conditioner_catalog(self, overwrite: bool = False):
        """
        Создает полный и объединенный каталог кондиционеров из всех источников (Excel, PDF).

        Args:
            overwrite (bool): Если True, перезапишет существующий файл каталога.
        """
        if os.path.exists(self.air_conditioner_catalog_path) and not overwrite:
            self.logger.warning(f"Каталог {self.air_conditioner_catalog_path} уже существует. Используйте `overwrite=True`.")
            return

        self.logger.info("Начало создания полного каталога кондиционеров...")
        
        # 1. Извлечение данных
        xlsx_data = self._extract_data_from_xlsx(self.excel_path)
        pdf_data = self._extract_data_from_pdfs(self.pdf_path)
        
        # 2. Обработка и слияние
        unique_models = {}
        self.logger.info(f"Обработка {len(xlsx_data)} записей из Excel...")
        
        for row in xlsx_data:
            model_info = self._extract_model_info_from_xlsx_row(row)
            if not model_info or not model_info.get('model_name'):
                continue
                
            model_key = self._normalize_model_name(model_info['model_name'])
            if model_key not in unique_models:
                # Новая модель
                pdf_info = self._find_matching_pdf_info(model_info['model_name'], pdf_data)
                
                unique_models[model_key] = {
                    'model_name': model_info['model_name'],
                    'brand': model_info['brand'],
                    'series': model_info['series'],
                    'specifications': {
                        'cooling_power_kw': model_info['cooling_power_kw'],
                        'heating_power_kw': model_info['heating_power_kw'],
                        'cooling_consumption_kw': model_info['cooling_consumption_kw'],
                        'heating_consumption_kw': model_info['heating_consumption_kw'],
                    },
                    'pricing': {
                        'dealer_price_usd': model_info['dealer_price_usd'],
                        'retail_price_byn': model_info['retail_price_byn'],
                    },
                    'suppliers': [model_info['supplier']],
                    'description': pdf_info.get('description', ''),
                    'representative_image': pdf_info.get('image', None),
                    'last_updated': datetime.now().isoformat(),
                    'air_description': '' # Будет заполнено позже
                }
            else:
                # Существующая модель, добавляем поставщика
                existing_model = unique_models[model_key]
                existing_model['suppliers'].append(model_info['supplier'])
                # Можно добавить логику обновления цен, если новые свежее
        
        # 3. Формирование и сохранение каталога
        final_list = list(unique_models.values())
        catalog_structure = {
            "catalog_info": {
                "name": "Полный каталог кондиционеров",
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_models": len(final_list)
            },
            "air_conditioners": final_list
        }
        
        self._save_json(catalog_structure, self.air_conditioner_catalog_path)
        self.logger.info(f"Создан полный каталог с {len(final_list)} уникальными моделями.")
        
        # 4. Обогащение описаний (можно вызывать как отдельный шаг)
        self.enrich_air_conditioner_descriptions()
        
    def _extract_model_info_from_xlsx_row(self, row: Dict) -> Optional[Dict]:
        """Извлекает и структурирует информацию о модели из одной строки Excel."""
        # Логика поиска полей модели, цены, характеристик
        # Это одна из самых сложных частей, так как структура файлов разная
        # Используем комбинацию имен столбцов и ключевых слов
        model_name, brand, series = None, None, None
        
        # Поиск названия модели
        model_keywords = ['модель', 'наименование', 'model', 'article']
        for key, value in row.items():
            if any(kw in str(key).lower() for kw in model_keywords):
                if value and isinstance(value, str) and len(value) > 3:
                    model_name = value
                    break
        # Если не нашли по заголовку, ищем по содержимому (эвристика)
        if not model_name:
            for val in row.values():
                if isinstance(val, str) and re.search(r'[A-Z]{2,}-\d+', val):
                    model_name = val
                    break
        
        if not model_name: return None
        
        # Определение бренда
        brand_list = ['DANTEX', 'MITSUBISHI', 'TCL', 'HISENSE', 'MIDEA', 'ELECTROLUX', 'SAMSUNG', 'TOSHIBA']
        for b in brand_list:
            if b in model_name.upper():
                brand = b
                break
        if not brand:
            brand = "Unknown"

        # Извлечение данных (упрощенная версия)
        return {
            'model_name': self._clean_text(model_name),
            'brand': brand,
            'series': '', # Логику извлечения серии можно добавить здесь
            'cooling_power_kw': self._extract_numeric_value(row.get('Мощность охл., кВт')),
            'heating_power_kw': self._extract_numeric_value(row.get('Мощность обогр., кВт')),
            'cooling_consumption_kw': self._extract_numeric_value(row.get('Потребл. мощность (охл.)')),
            'heating_consumption_kw': self._extract_numeric_value(row.get('Потребл. мощность (обогр.)')),
            'dealer_price_usd': self._extract_numeric_value(row.get('Дилер USD')),
            'retail_price_byn': self._extract_numeric_value(row.get('Розница BYN')),
            'supplier': {
                'name': row.get('_source_file', 'Unknown Source'),
                'price': self._extract_numeric_value(row.get('Розница BYN')),
                'currency': 'BYN'
            }
        }

    def _find_matching_pdf_info(self, model_name: str, pdf_data: List[Dict]) -> Dict:
        """Находит релевантную информацию для модели в данных из PDF."""
        norm_model = self._normalize_model_name(model_name)
        for pdf in pdf_data:
            if norm_model in self._normalize_model_name(pdf['text_content']):
                # Нашли совпадение, извлекаем описание и изображение
                return {
                    "description": self._clean_text(pdf['text_content'][:500]), # Простое извлечение
                    "image": pdf['images'][0]['path'] if pdf['images'] else None
                }
        return {}
    
    def enrich_air_conditioner_descriptions(self):
        """
        Обогащает каталог кондиционеров генерируемыми описаниями.
        """
        self.logger.info("Начало обогащения описаний кондиционеров...")
        catalog = self._load_json(self.air_conditioner_catalog_path)
        if not catalog or 'air_conditioners' not in catalog:
            self.logger.error("Каталог кондиционеров не загружен или пуст.")
            return

        for aircon in catalog['air_conditioners']:
            aircon['air_description'] = self._generate_enhanced_air_description(aircon)
            aircon['last_updated'] = datetime.now().isoformat()
        
        self._save_json(catalog, self.air_conditioner_catalog_path)
        self.logger.info("Описания кондиционеров успешно обогащены и сохранены.")

    def _generate_enhanced_air_description(self, model_data: Dict) -> str:
        """Генерирует расширенное, читаемое описание для одного кондиционера."""
        brand_desc = self._get_brand_descriptions().get(model_data.get('brand', '').upper(), '')
        
        parts = [f"Кондиционер {model_data.get('brand', '')} {model_data.get('model_name', '')}."]
        
        specs = model_data.get('specifications', {})
        if specs.get('cooling_power_kw'):
            parts.append(f"Мощность охлаждения составляет {specs['cooling_power_kw']} кВт.")
        if 'inverter' in model_data.get('model_name', '').lower():
            parts.append("Оснащен современной инверторной технологией для точного поддержания температуры и экономии электроэнергии.")
        
        parts.append(brand_desc)
        
        # Удаляем пустые строки и объединяем
        return ' '.join(filter(None, parts))

    def _get_brand_descriptions(self) -> Dict[str, str]:
        """Возвращает статические описания брендов."""
        return {
            'DANTEX': 'Dantex - производитель климатической техники с оптимальным соотношением цена-качество.',
            'MITSUBISHI': 'Mitsubishi - японский гигант, известный своей надежностью и передовыми технологиями в области кондиционирования.',
            # ... и так далее
        }
        
    def validate_air_conditioner_catalog_with_excel(self):
        """
        Валидирует существующий каталог кондиционеров, сверяя его с данными из Excel.
        Модели, не найденные в Excel, помечаются или удаляются.
        """
        self.logger.info("Начало валидации каталога кондиционеров по Excel-файлам...")
        catalog = self._load_json(self.air_conditioner_catalog_path)
        if not catalog or 'air_conditioners' not in catalog:
            self.logger.error("Каталог для валидации не загружен.")
            return

        # Загружаем все данные из Excel в кэш, если его еще нет
        if not self._excel_data_cache:
            all_excel_dfs = self._load_all_excel_sheets_to_cache(self.excel_path)
        
        validated_aircons = []
        found, not_found, updated = 0, 0, 0

        for aircon in catalog['air_conditioners']:
            model_name = aircon.get('model_name')
            match_data = self._find_model_in_excel_cache(model_name)
            
            if match_data:
                # Нашли, обновляем данные
                aircon['pricing'].update(match_data.get('pricing', {}))
                aircon['specifications'].update(match_data.get('specifications', {}))
                aircon['last_updated'] = datetime.now().isoformat()
                aircon['validation_status'] = 'found_and_updated'
                validated_aircons.append(aircon)
                found += 1
                updated +=1
            else:
                # Не нашли
                self.logger.warning(f"Модель '{model_name}' не найдена в Excel-источниках. Помечаем как невалидную.")
                aircon['validation_status'] = 'not_found'
                # Можно либо добавить в список, либо пропустить (удалить)
                # validated_aircons.append(aircon)
                not_found += 1
        
        catalog['air_conditioners'] = validated_aircons
        catalog['catalog_info']['last_validated'] = datetime.now().isoformat()
        self._save_json(catalog, self.air_conditioner_catalog_path)
        self.logger.info(f"Валидация завершена. Найдено: {found}, Не найдено: {not_found}, Обновлено: {updated}.")
    
    def _load_all_excel_sheets_to_cache(self, directory: str):
        """Загружает все листы из всех Excel файлов в кеш self._excel_data_cache."""
        self.logger.info(f"Кэширование данных из Excel-файлов в директории: {directory}")
        if not os.path.exists(directory):
            self.logger.warning(f"Директория для кэширования не найдена: {directory}")
            return
            
        for filename in os.listdir(directory):
            if filename.endswith('.xlsx') and not filename.startswith('~$'):
                file_path = os.path.join(directory, filename)
                try:
                    xls = pd.ExcelFile(file_path)
                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(xls, sheet_name=sheet_name)
                        df['_source_file'] = filename
                        df['_source_sheet'] = sheet_name
                        self._excel_data_cache[f"{filename}_{sheet_name}"] = df
                except Exception as e:
                    self.logger.error(f"Ошибка при кэшировании файла {filename}: {e}")

    def _find_model_in_excel_cache(self, model_name: str) -> Optional[Dict]:
        """Ищет модель в закэшированных данных Excel."""
        if not model_name: return None
        norm_model = self._normalize_model_name(model_name)

        for source, df in self._excel_data_cache.items():
            for _, row in df.iterrows():
                # Проходимся по всем ячейкам строки в поисках совпадения
                for cell_value in row.values:
                    if norm_model == self._normalize_model_name(str(cell_value)):
                        # Нашли совпадение, извлекаем информацию из этой строки
                        return self._extract_model_info_from_xlsx_row(row.to_dict())
        return None
        
    @staticmethod
    def _clean_text(text: Any) -> str:
        """Очищает текст от лишних символов и пробелов."""
        if not text or pd.isna(text):
            return ""
        return str(text).strip().replace('\n', ' ').replace('\r', '')

# ==============================================================================
# Демонстрация использования класса
# ==============================================================================
if __name__ == '__main__':
    # Пример реализации кастомного логгера, который можно вынести в utils/mylogger.py
    # Это сделано для того, чтобы скрипт был полностью рабочим "из коробки".
    class MyLogger:
        def __init__(self, name="DefaultLogger", log_file="default.log", level=logging.INFO):
            self.logger = logging.getLogger(name)
            self.logger.setLevel(level)
            
            # Предотвращаем дублирование хендлеров
            if not self.logger.handlers:
                # Консольный хендлер
                ch = logging.StreamHandler()
                ch.setLevel(level)
                
                # Файловый хендлер
                fh = logging.FileHandler(log_file, encoding='utf-8')
                fh.setLevel(level)
                
                # Форматтер
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                ch.setFormatter(formatter)
                fh.setFormatter(formatter)
                
                self.logger.addHandler(ch)
                self.logger.addHandler(fh)

        def info(self, msg): self.logger.info(msg)
        def warning(self, msg): self.logger.warning(msg)
        def error(self, msg): self.logger.error(msg)
        def exception(self, msg): self.logger.exception(msg)
        def debug(self, msg): self.logger.debug(msg)

    # Заменяем заглушку на реальную реализацию
    Logger = MyLogger

    # Создаем экземпляр главного класса
    data_manager = ComprehensiveDataManager(base_path='docs')
    
    # --- Демонстрационный пайплайн ---
    
    print("\n" + "="*50)
    print("ШАГ 1: Работа с каталогом КОМПЛЕКТУЮЩИХ")
    print("="*50)
    # 1.1 Создаем начальный каталог комплектующих (если его нет)
    data_manager.create_initial_components_catalog(overwrite=False)
    
    # 1.2 Генерируем для них изображения-заглушки
    data_manager.generate_component_image_placeholders(overwrite=False)

    # 1.3 Извлекаем реальные изображения из Excel
    # Укажите реальный путь к вашему Excel-файлу с изображениями комплектующих
    components_excel_path = os.path.join(data_manager.excel_path, 'стоимости материалов кондиц.xlsx')
    if os.path.exists(components_excel_path):
         data_manager.extract_images_from_xlsx_zip(components_excel_path, data_manager.images_comp_path)
    else:
        print(f"INFO: Файл {components_excel_path} для извлечения изображений комплектующих не найден, шаг пропущен.")

    print("\n" + "="*50)
    print("ШАГ 2: Работа с каталогом КОНДИЦИОНЕРОВ")
    print("="*50)
    
    # 2.1 Создаем полный каталог кондиционеров из всех источников
    # Этот метод уже включает в себя извлечение из Excel, PDF и первичное обогащение
    data_manager.create_full_air_conditioner_catalog(overwrite=True) # True для демонстрации
    
    # 2.2 Проводим дополнительную валидацию созданного каталога
    # Этот шаг сверяет записи в созданном JSON с прайс-листами и обновляет их
    data_manager.validate_air_conditioner_catalog_with_excel()

    print("\n" + "="*50)
    print("✅ Все операции завершены.")
    print(f"Проверьте результаты в папке: {data_manager.base_path}")
    print(f"Лог-файл находится здесь: {data_manager.class_name.lower()}.log")
    print("="*50)