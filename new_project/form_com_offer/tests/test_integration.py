"""
Интеграционные тесты для проверки взаимодействия компонентов
"""
import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from back.back import app
from db.database import get_session
from db import crud, models, schemas
from datetime import date
from utils.pdf_generator import generate_offer_pdf
from utils.compose_pdf_generator import generate_compose_offer_pdf


class TestIntegration:
    """Интеграционные тесты"""
    
    @pytest.fixture
    def client(self):
        """Фикстура для создания тестового клиента"""
        return TestClient(app)
    
    @pytest.fixture
    async def db_session(self):
        """Фикстура для создания сессии базы данных"""
        async for session in get_session():
            yield session
            await session.rollback()
    
    @pytest.mark.asyncio
    async def test_full_order_workflow(self, client, db_session):
        """Тест полного рабочего процесса для обычного заказа"""
        # 1. Создаем заказ
        order_data = {
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
                }
            ],
            "comment": "Тестовый комментарий"
        }
        
        response = client.post("/api/save_order/", json=order_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        order_id = data["order_id"]
        
        # 2. Обновляем комментарий
        comment_update = {
            "id": order_id,
            "comment": "Обновленный комментарий"
        }
        
        response = client.post("/api/save_order/", json=comment_update)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # 3. Получаем заказ и проверяем обновление
        response = client.get(f"/api/order/{order_id}")
        assert response.status_code == 200
        
        order = response.json()
        assert order["comment"] == "Обновленный комментарий"
        
        # 4. Генерируем PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            result_path = generate_offer_pdf(order, pdf_path)
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
        finally:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    @pytest.mark.asyncio
    async def test_full_compose_order_workflow(self, client, db_session):
        """Тест полного рабочего процесса для составного заказа"""
        # 1. Создаем составной заказ
        compose_order_data = {
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
                }
            ],
            "comment": "Тестовый комментарий для составного заказа"
        }
        
        response = client.post("/api/save_compose_order/", json=compose_order_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        order_id = data["order_id"]
        
        # 2. Добавляем кондиционер
        aircon_data = {
            "order_id": order_id,
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
        
        response = client.post("/api/add_aircon_to_compose_order/", json=aircon_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # 3. Обновляем только комментарий
        comment_update = {
            "id": order_id,
            "comment": "Обновленный комментарий для составного заказа"
        }
        
        response = client.post("/api/save_compose_order/", json=comment_update)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # 4. Обновляем только компоненты
        components_update = {
            "id": order_id,
            "components": [
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
            "status": "completely filled"
        }
        
        response = client.post("/api/save_compose_order/", json=components_update)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # 5. Получаем составной заказ и проверяем обновления
        response = client.get(f"/api/compose_order/{order_id}")
        assert response.status_code == 200
        
        order = response.json()
        assert order["compose_order_data"]["comment"] == "Обновленный комментарий для составного заказа"
        assert len(order["compose_order_data"]["airs"]) == 2
        assert len(order["compose_order_data"]["components"]) == 1
        assert order["compose_order_data"]["components"][0]["name"] == "труба 9,52х0,76 (3/8'') мм"
        
        # 6. Генерируем PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        try:
            result_path = generate_compose_offer_pdf(order["compose_order_data"], pdf_path)
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
        finally:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
    
    @pytest.mark.asyncio
    async def test_frontend_backend_integration(self, client, db_session):
        """Тест интеграции фронтенда и бэкенда"""
        # Создаем заказ через API
        order_data = {
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
            "comment": "Тестовый комментарий"
        }
        
        response = client.post("/api/save_order/", json=order_data)
        assert response.status_code == 200
        
        data = response.json()
        order_id = data["order_id"]
        
        # Симулируем фронтенд запросы
        from front.front import fill_fields_from_order_diff, fill_components_fields_from_order
        
        # Получаем заказ
        response = client.get(f"/api/order/{order_id}")
        assert response.status_code == 200
        
        order = response.json()
        
        # Тестируем функции фронтенда с данными от бэкенда
        fields_updates = fill_fields_from_order_diff(order)
        assert fields_updates["name"] == "Тест Клиент"
        assert fields_updates["phone"] == "+375001234567"
        assert fields_updates["comment"] == "Тестовый комментарий"
        
        # Тестируем заполнение компонентов
        components_catalog = {
            "components": [
                {
                    "name": "труба 6,35х0,76 (1/4'') мм",
                    "price": 9.93,
                    "currency": "BYN",
                    "unit": "м."
                }
            ]
        }
        
        comp_updates = fill_components_fields_from_order(order, components_catalog)
        assert len(comp_updates) == 3  # 1 компонент * 3 поля
    
    @pytest.mark.asyncio
    async def test_database_api_integration(self, client, db_session):
        """Тест интеграции базы данных и API"""
        # Создаем клиента через CRUD
        client_data = schemas.ClientCreate(
            full_name="Тест Клиент",
            phone="+375001234567",
            email="test@example.com",
            address="Тестовый адрес"
        )
        
        client_db = await crud.create_client(db_session, client_data)
        assert client_db.id is not None
        
        # Создаем заказ через API
        order_data = {
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
            "comment": "Тестовый комментарий"
        }
        
        response = client.post("/api/save_order/", json=order_data)
        assert response.status_code == 200
        
        data = response.json()
        order_id = data["order_id"]
        
        # Проверяем, что заказ сохранился в базе данных
        order_db = await crud.get_order_by_id(db_session, order_id)
        assert order_db is not None
        assert order_db.client_id == client_db.id
        
        # Проверяем данные заказа
        order_data_db = json.loads(order_db.order_data)
        assert order_data_db["client_data"]["full_name"] == "Тест Клиент"
        assert order_data_db["comment"] == "Тестовый комментарий"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, client, db_session):
        """Тест обработки ошибок в интеграции"""
        # Тестируем сохранение заказа с некорректными данными
        invalid_order_data = {
            "client_data": {
                "full_name": "",  # Пустое имя
                "phone": "invalid_phone",  # Некорректный телефон
                "email": "invalid_email",  # Некорректный email
                "address": "Тестовый адрес"
            },
            "order_params": {
                "room_area": -50,  # Отрицательная площадь
                "room_type": "квартира",
                "discount": 150,  # Слишком большая скидка
                "visit_date": "invalid_date",  # Некорректная дата
                "installation_price": -100  # Отрицательная цена
            },
            "aircon_params": {
                "wifi": True,
                "inverter": False,
                "price_limit": -15000,  # Отрицательный лимит
                "brand": "Любой",
                "mount_type": "Любой",
                "area": -50,  # Отрицательная площадь
                "ceiling_height": -2.7,  # Отрицательная высота
                "illumination": "Средняя",
                "num_people": -2,  # Отрицательное количество людей
                "activity": "Сидячая работа",
                "num_computers": -1,  # Отрицательное количество компьютеров
                "num_tvs": -1,  # Отрицательное количество телевизоров
                "other_power": -500  # Отрицательная мощность
            },
            "components": [],
            "comment": "Тестовый комментарий"
        }
        
        response = client.post("/api/save_order/", json=invalid_order_data)
        # API должен обработать некорректные данные и вернуть ошибку или валидировать их
        assert response.status_code in [200, 422, 400]
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, client, db_session):
        """Тест конкурентных операций"""
        import asyncio
        import concurrent.futures
        
        # Создаем несколько заказов одновременно
        order_data_template = {
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
            "comment": "Тестовый комментарий"
        }
        
        def create_order(order_num):
            order_data = order_data_template.copy()
            order_data["client_data"]["full_name"] = f"Тест Клиент {order_num}"
            order_data["client_data"]["phone"] = f"+37500123456{order_num}"
            order_data["comment"] = f"Тестовый комментарий {order_num}"
            
            response = client.post("/api/save_order/", json=order_data)
            return response.json()
        
        # Создаем 5 заказов одновременно
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_order, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Проверяем, что все заказы создались успешно
        for result in results:
            assert result["success"] is True
            assert result["order_id"] > 0
        
        # Проверяем, что все заказы уникальны
        order_ids = [result["order_id"] for result in results]
        assert len(set(order_ids)) == 5
    
    @pytest.mark.asyncio
    async def test_data_consistency(self, client, db_session):
        """Тест согласованности данных"""
        # Создаем заказ
        order_data = {
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
                }
            ],
            "comment": "Тестовый комментарий"
        }
        
        response = client.post("/api/save_order/", json=order_data)
        assert response.status_code == 200
        
        data = response.json()
        order_id = data["order_id"]
        
        # Получаем заказ через API
        response = client.get(f"/api/order/{order_id}")
        assert response.status_code == 200
        
        order_api = response.json()
        
        # Получаем заказ через CRUD
        order_db = await crud.get_order_by_id(db_session, order_id)
        order_data_db = json.loads(order_db.order_data)
        
        # Проверяем согласованность данных
        assert order_api["client_data"]["full_name"] == order_data_db["client_data"]["full_name"]
        assert order_api["client_data"]["phone"] == order_data_db["client_data"]["phone"]
        assert order_api["order_params"]["room_area"] == order_data_db["order_params"]["room_area"]
        assert order_api["aircon_params"]["wifi"] == order_data_db["aircon_params"]["wifi"]
        assert order_api["comment"] == order_data_db["comment"]
        assert len(order_api["components"]) == len(order_data_db["components"])
        
        # Проверяем компоненты
        for i, component in enumerate(order_api["components"]):
            db_component = order_data_db["components"][i]
            assert component["name"] == db_component["name"]
            assert component["selected"] == db_component["selected"]
            assert component["qty"] == db_component["qty"]
            assert component["length"] == db_component["length"]
            assert component["price"] == db_component["price"]
