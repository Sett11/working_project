#!/usr/bin/env python3
"""
Unit-тесты для валидации каталога компонентов.
"""

import unittest
import json
import tempfile
import os
import sys

# Добавляем путь к модулю для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_catalog import validate_components_catalog

class TestCatalogValidation(unittest.TestCase):
    """Тесты для валидации каталога компонентов"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.valid_catalog = {
            "components": [
                {"id": 1, "name": "Компонент 1", "category": "Категория 1"},
                {"id": 2, "name": "Компонент 2", "category": "Категория 1"},
                {"id": 3, "name": "Компонент 3", "category": "Категория 2"}
            ]
        }
        
        self.duplicate_ids_catalog = {
            "components": [
                {"id": 1, "name": "Компонент 1", "category": "Категория 1"},
                {"id": 1, "name": "Компонент 2", "category": "Категория 1"},  # Дублирующийся ID
                {"id": 3, "name": "Компонент 3", "category": "Категория 2"}
            ]
        }
        
        self.duplicate_names_catalog = {
            "components": [
                {"id": 1, "name": "Компонент 1", "category": "Категория 1"},
                {"id": 2, "name": "Компонент 1", "category": "Категория 1"},  # Дублирующееся имя
                {"id": 3, "name": "Компонент 3", "category": "Категория 2"}
            ]
        }
        
        self.missing_ids_catalog = {
            "components": [
                {"id": 1, "name": "Компонент 1", "category": "Категория 1"},
                {"name": "Компонент 2", "category": "Категория 1"},  # Отсутствует ID
                {"id": 3, "name": "Компонент 3", "category": "Категория 2"}
            ]
        }
        
        self.empty_catalog = {
            "components": []
        }
        
        self.invalid_catalog = {
            "wrong_key": []
        }
    
    def create_temp_catalog_file(self, catalog_data):
        """Создает временный файл каталога для тестирования"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(catalog_data, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()
        return temp_file.name
    
    def test_valid_catalog(self):
        """Тест валидного каталога"""
        temp_file = self.create_temp_catalog_file(self.valid_catalog)
        try:
            result = validate_components_catalog(temp_file)
            self.assertTrue(result, "Валидный каталог должен пройти проверку")
        finally:
            os.unlink(temp_file)
    
    def test_duplicate_ids(self):
        """Тест каталога с дублирующимися ID"""
        temp_file = self.create_temp_catalog_file(self.duplicate_ids_catalog)
        try:
            result = validate_components_catalog(temp_file)
            self.assertFalse(result, "Каталог с дублирующимися ID должен не пройти проверку")
        finally:
            os.unlink(temp_file)
    
    def test_duplicate_names(self):
        """Тест каталога с дублирующимися именами"""
        temp_file = self.create_temp_catalog_file(self.duplicate_names_catalog)
        try:
            result = validate_components_catalog(temp_file)
            self.assertFalse(result, "Каталог с дублирующимися именами должен не пройти проверку")
        finally:
            os.unlink(temp_file)
    
    def test_missing_ids(self):
        """Тест каталога с отсутствующими ID"""
        temp_file = self.create_temp_catalog_file(self.missing_ids_catalog)
        try:
            result = validate_components_catalog(temp_file)
            self.assertFalse(result, "Каталог с отсутствующими ID должен не пройти проверку")
        finally:
            os.unlink(temp_file)
    
    def test_empty_catalog(self):
        """Тест пустого каталога"""
        temp_file = self.create_temp_catalog_file(self.empty_catalog)
        try:
            result = validate_components_catalog(temp_file)
            self.assertTrue(result, "Пустой каталог должен пройти проверку")
        finally:
            os.unlink(temp_file)
    
    def test_invalid_catalog_structure(self):
        """Тест каталога с неверной структурой"""
        temp_file = self.create_temp_catalog_file(self.invalid_catalog)
        try:
            result = validate_components_catalog(temp_file)
            self.assertFalse(result, "Каталог с неверной структурой должен не пройти проверку")
        finally:
            os.unlink(temp_file)
    
    def test_nonexistent_file(self):
        """Тест несуществующего файла"""
        result = validate_components_catalog("/nonexistent/file.json")
        self.assertFalse(result, "Несуществующий файл должен не пройти проверку")
    
    def test_invalid_json_file(self):
        """Тест файла с неверным JSON"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write(b"invalid json content")
        temp_file.close()
        
        try:
            result = validate_components_catalog(temp_file.name)
            self.assertFalse(result, "Файл с неверным JSON должен не пройти проверку")
        finally:
            os.unlink(temp_file.name)

if __name__ == "__main__":
    # Запуск тестов
    unittest.main(verbosity=2)
