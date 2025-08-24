"""
Тесты для генерации PDF документов
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from utils.compose_pdf_generator import generate_compose_offer_pdf
from utils.pdf_generator import generate_offer_pdf


class TestPDFGeneration:
    """Тесты для генерации PDF документов"""
    
    @pytest.fixture
    def sample_order_data(self):
        """Фикстура с тестовыми данными заказа"""
        return {
            "client_data": {
                "full_name": "Тест Клиент",
                "phone": "+375001234567",
                "email": "test@example.com",
                "address": "Тестовый адрес"
            },
            "order_params": {
                "room_area": 50,
                "room_type": "квартира",
                "discount": 5,
                "visit_date": "2025-01-01",
                "installation_price": 100
            },
            "aircon_params": {
                "wifi": True,
                "inverter": False,
                "price_limit": 15000,
                "brand": "Любой",
                "mount_type": "Любой",
                "area": 50,
                "ceiling_height": 2.7,
                "illumination": "Средняя",
                "num_people": 2,
                "activity": "Сидячая работа",
                "num_computers": 1,
                "num_tvs": 1,
                "other_power": 500
            },
            "components": [
                {
                    "name": "труба 6,35х0,76 (1/4'') мм",
                    "selected": True,
                    "qty": 1,
                    "length": 10,
                    "price": 9.93,
                    "currency": "BYN",
                    "unit": "м."
                },
                {
                    "name": "труба 9,52х0,76 (3/8'') мм",
                    "selected": False,
                    "qty": 0,
                    "length": 0,
                    "price": 12.50,
                    "currency": "BYN",
                    "unit": "м."
                }
            ],
            "comment": "Тестовый комментарий"
        }
    
    @pytest.fixture
    def sample_compose_order_data(self):
        """Фикстура с тестовыми данными составного заказа"""
        return {
            "client_data": {
                "full_name": "Тест Клиент",
                "phone": "+375001234567",
                "email": "test@example.com",
                "address": "Тестовый адрес"
            },
            "order_params": {
                "visit_date": "2025-01-01",
                "discount": 5
            },
            "airs": [
                {
                    "order_params": {
                        "room_area": 50,
                        "room_type": "квартира",
                        "installation_price": 100
                    },
                    "aircon_params": {
                        "wifi": True,
                        "inverter": False,
                        "price_limit": 15000,
                        "brand": "Любой",
                        "mount_type": "Любой",
                        "area": 50,
                        "ceiling_height": 2.7,
                        "illumination": "Средняя",
                        "num_people": 2,
                        "activity": "Сидячая работа",
                        "num_computers": 1,
                        "num_tvs": 1,
                        "other_power": 500
                    }
                },
                {
                    "order_params": {
                        "room_area": 30,
                        "room_type": "квартира",
                        "installation_price": 80
                    },
                    "aircon_params": {
                        "wifi": False,
                        "inverter": True,
                        "price_limit": 12000,
                        "brand": "Midea",
                        "mount_type": "Настенный",
                        "area": 30,
                        "ceiling_height": 2.5,
                        "illumination": "Низкая",
                        "num_people": 1,
                        "activity": "Сидячая работа",
                        "num_computers": 0,
                        "num_tvs": 1,
                        "other_power": 200
                    }
                }
            ],
            "components": [
                {
                    "name": "труба 6,35х0,76 (1/4'') мм",
                    "selected": True,
                    "qty": 1,
                    "length": 10,
                    "price": 9.93,
                    "currency": "BYN",
                    "unit": "м."
                },
                {
                    "name": "труба 9,52х0,76 (3/8'') мм",
                    "selected": True,
                    "qty": 2,
                    "length": 15,
                    "price": 12.50,
                    "currency": "BYN",
                    "unit": "м."
                }
            ],
            "comment": "Тестовый комментарий для составного заказа"
        }
    
    def test_generate_offer_pdf(self, sample_order_data):
        """Тест генерации PDF для обычного заказа"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_offer_pdf(sample_order_data, pdf_path)
            
            # Проверяем, что файл создался
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
            # Проверяем, что путь возвращается правильно
            assert result_path == pdf_path
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_generate_compose_offer_pdf(self, sample_compose_order_data):
        """Тест генерации PDF для составного заказа"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_compose_offer_pdf(sample_compose_order_data, pdf_path)
            
            # Проверяем, что файл создался
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
            # Проверяем, что путь возвращается правильно
            assert result_path == pdf_path
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_generate_offer_pdf_with_components(self, sample_order_data):
        """Тест генерации PDF с компонентами"""
        # Добавляем больше компонентов для тестирования
        sample_order_data["components"].extend([
            {
                "name": "Кабель ВВГнг(А)-LS 3х1,5",
                "selected": True,
                "qty": 1,
                "length": 20,
                "price": 15.00,
                "currency": "BYN",
                "unit": "м."
            },
            {
                "name": "Дренажный насос CASPIA HOME",
                "selected": True,
                "qty": 1,
                "length": 1,
                "price": 150.00,
                "currency": "BYN",
                "unit": "шт."
            }
        ])
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_offer_pdf(sample_order_data, pdf_path)
            
            # Проверяем, что файл создался
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_generate_compose_offer_pdf_with_multiple_airs(self, sample_compose_order_data):
        """Тест генерации PDF для составного заказа с несколькими кондиционерами"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_compose_offer_pdf(sample_compose_order_data, pdf_path)
            
            # Проверяем, что файл создался
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_generate_offer_pdf_empty_components(self, sample_order_data):
        """Тест генерации PDF с пустым списком компонентов"""
        sample_order_data["components"] = []
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_offer_pdf(sample_order_data, pdf_path)
            
            # Проверяем, что файл создался
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_generate_compose_offer_pdf_empty_airs(self, sample_compose_order_data):
        """Тест генерации PDF для составного заказа с пустым списком кондиционеров"""
        sample_compose_order_data["airs"] = []
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_compose_offer_pdf(sample_compose_order_data, pdf_path)
            
            # Проверяем, что файл создался
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_generate_offer_pdf_missing_fields(self):
        """Тест генерации PDF с отсутствующими полями"""
        # Создаем данные с минимальным набором полей
        minimal_data = {
            "client_data": {
                "full_name": "Тест Клиент",
                "phone": "+375001234567",
                "email": "test@example.com",
                "address": "Тестовый адрес"
            },
            "order_params": {
                "room_area": 50,
                "room_type": "квартира",
                "discount": 5,
                "visit_date": "2025-01-01",
                "installation_price": 100
            },
            "aircon_params": {
                "wifi": True,
                "inverter": False,
                "price_limit": 15000,
                "brand": "Любой",
                "mount_type": "Любой",
                "area": 50,
                "ceiling_height": 2.7,
                "illumination": "Средняя",
                "num_people": 2,
                "activity": "Сидячая работа",
                "num_computers": 1,
                "num_tvs": 1,
                "other_power": 500
            },
            "components": [],
            "comment": ""
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_offer_pdf(minimal_data, pdf_path)
            
            # Проверяем, что файл создался
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_generate_compose_offer_pdf_missing_fields(self):
        """Тест генерации PDF для составного заказа с отсутствующими полями"""
        # Создаем данные с минимальным набором полей
        minimal_data = {
            "client_data": {
                "full_name": "Тест Клиент",
                "phone": "+375001234567",
                "email": "test@example.com",
                "address": "Тестовый адрес"
            },
            "order_params": {
                "visit_date": "2025-01-01",
                "discount": 5
            },
            "airs": [],
            "components": [],
            "comment": ""
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_compose_offer_pdf(minimal_data, pdf_path)
            
            # Проверяем, что файл создался
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_pdf_file_permissions(self, sample_order_data):
        """Тест прав доступа к созданному PDF файлу"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_offer_pdf(sample_order_data, pdf_path)
            
            # Проверяем, что файл доступен для чтения
            assert os.access(result_path, os.R_OK)
            
            # Проверяем, что файл доступен для записи (для возможного удаления)
            assert os.access(result_path, os.W_OK)
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_pdf_content_validation(self, sample_order_data):
        """Тест валидации содержимого PDF"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Генерируем PDF
            result_path = generate_offer_pdf(sample_order_data, pdf_path)
            
            # Проверяем, что файл не пустой
            assert os.path.getsize(result_path) > 1000  # Минимальный размер для PDF
            
            # Проверяем, что файл начинается с PDF сигнатуры
            with open(result_path, 'rb') as f:
                header = f.read(4)
                assert header == b'%PDF'
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    @patch('utils.pdf_generator.PdfPages')
    def test_pdf_generation_error_handling(self, mock_pdf_pages, sample_order_data):
        """Тест обработки ошибок при генерации PDF"""
        # Мокаем ошибку при создании PDF
        mock_pdf_pages.side_effect = Exception("PDF generation error")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            # Проверяем, что функция обрабатывает ошибки
            with pytest.raises(Exception):
                generate_offer_pdf(sample_order_data, pdf_path)
            
        finally:
            # Удаляем временный файл
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    def test_pdf_filename_validation(self, sample_order_data):
        """Тест валидации имени файла PDF"""
        # Тестируем с различными именами файлов
        test_filenames = [
            "test.pdf",
            "test_offer.pdf",
            "commercial_offer_123.pdf",
            "КП_заказ_1.pdf"
        ]
        
        for filename in test_filenames:
            with tempfile.NamedTemporaryFile(suffix=f'_{filename}', delete=False) as tmp_file:
                pdf_path = tmp_file.name
            
            try:
                # Генерируем PDF
                result_path = generate_offer_pdf(sample_order_data, pdf_path)
                
                # Проверяем, что файл создался
                assert os.path.exists(result_path)
                assert os.path.getsize(result_path) > 0
                
            finally:
                # Удаляем временный файл
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
