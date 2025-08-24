"""
Тесты для API эндпоинтов
"""
import pytest
import httpx
import json
from fastapi.testclient import TestClient
from back.back import app
from db.database import get_session
from db import crud, models, schemas
from datetime import date


class TestAPI:
    """Тесты для API эндпоинтов"""
    
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
    
    def test_health_endpoint(self, client):
        """Тест эндпоинта /health"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "pool_stats" in data
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
    
    def test_recreate_pool_endpoint(self, client):
        """Тест эндпоинта /api/recreate_pool"""
        response = client.post("/api/recreate_pool")
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_save_order_endpoint(self, client, db_session):
        """Тест эндпоинта /api/save_order/"""
        # Создаем тестовые данные заказа
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
        
        # Тестируем создание нового заказа
        response = client.post("/api/save_order/", json=order_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "order_id" in data
        assert data["order_id"] > 0
        
        order_id = data["order_id"]
        
        # Тестируем обновление существующего заказа
        updated_order_data = order_data.copy()
        updated_order_data["id"] = order_id
        updated_order_data["comment"] = "Обновленный комментарий"
        
        response = client.post("/api/save_order/", json=updated_order_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "order_id" in data
        assert data["order_id"] == order_id
        
        # Тестируем обновление только комментария
        comment_update = {
            "id": order_id,
            "comment": "Только комментарий"
        }
        
        response = client.post("/api/save_order/", json=comment_update)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_save_compose_order_endpoint(self, client, db_session):
        """Тест эндпоинта /api/save_compose_order/"""
        # Создаем тестовые данные составного заказа
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
        
        # Тестируем создание нового составного заказа
        response = client.post("/api/save_compose_order/", json=compose_order_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "order_id" in data
        assert data["order_id"] > 0
        
        order_id = data["order_id"]
        
        # Тестируем обновление только комментария
        comment_update = {
            "id": order_id,
            "comment": "Обновленный комментарий для составного заказа"
        }
        
        response = client.post("/api/save_compose_order/", json=comment_update)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        
        # Тестируем обновление только компонентов
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
        assert "success" in data
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_compose_order_endpoint(self, client, db_session):
        """Тест эндпоинта /api/compose_order/{order_id}"""
        # Сначала создаем составной заказ
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
        order_id = data["order_id"]
        
        # Тестируем получение составного заказа
        response = client.get(f"/api/compose_order/{order_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["id"] == order_id
        assert "status" in data
        assert "compose_order_data" in data
        
        compose_data = data["compose_order_data"]
        assert compose_data["client_data"]["full_name"] == "Тест Клиент"
        assert len(compose_data["airs"]) == 1
        assert len(compose_data["components"]) == 1
        assert compose_data["comment"] == "Тестовый комментарий для составного заказа"
        
        # Тестируем получение несуществующего заказа
        response = client.get("/api/compose_order/99999")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_add_aircon_to_compose_order_endpoint(self, client, db_session):
        """Тест эндпоинта /api/add_aircon_to_compose_order/"""
        # Сначала создаем составной заказ
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
            "airs": [],
            "components": [],
            "comment": "Тестовый комментарий"
        }
        
        response = client.post("/api/save_compose_order/", json=compose_order_data)
        assert response.status_code == 200
        
        data = response.json()
        order_id = data["order_id"]
        
        # Тестируем добавление кондиционера
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
        assert "success" in data
        assert data["success"] is True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_all_orders_endpoint(self, client, db_session):
        """Тест эндпоинта /api/all_orders/"""
        # Создаем обычный заказ
        order_data = {
            "client_data": {
                "full_name": "Тест Клиент 1",
                "phone": "+375001234567",
                "email": "test1@example.com",
                "address": "Тестовый адрес 1"
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
        
        # Создаем составной заказ
        compose_order_data = {
            "client_data": {
                "full_name": "Тест Клиент 2",
                "phone": "+375001234568",
                "email": "test2@example.com",
                "address": "Тестовый адрес 2"
            },
            "order_params": {
                "visit_date": "2025-01-01",
                "discount": 5
            },
            "airs": [],
            "components": [],
            "comment": "Тестовый комментарий для составного заказа"
        }
        
        response = client.post("/api/save_compose_order/", json=compose_order_data)
        assert response.status_code == 200
        
        # Тестируем получение всех заказов
        response = client.get("/api/all_orders/")
        assert response.status_code == 200
        
        data = response.json()
        assert "orders" in data
        assert isinstance(data["orders"], list)
        
        # Проверяем, что в списке есть наши заказы
        orders = data["orders"]
        assert len(orders) >= 2
        
        # Ищем наши заказы
        found_regular = False
        found_compose = False
        
        for order in orders:
            if order["client_name"] == "Тест Клиент 1" and order["order_type"] == "Order":
                found_regular = True
            elif order["client_name"] == "Тест Клиент 2" and order["order_type"] == "ComposeOrder":
                found_compose = True
        
        assert found_regular, "Обычный заказ не найден в списке"
        assert found_compose, "Составной заказ не найден в списке"
    
    @pytest.mark.asyncio
    async def test_generate_compose_offer_endpoint(self, client, db_session):
        """Тест эндпоинта /api/generate_compose_offer/"""
        # Сначала создаем составной заказ с данными
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
        order_id = data["order_id"]
        
        # Тестируем генерацию КП
        response = client.post(f"/api/generate_compose_offer/{order_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "pdf_path" in data
        assert data["pdf_path"] is not None
        
        # Проверяем, что файл PDF создался
        import os
        assert os.path.exists(data["pdf_path"])
    
    def test_invalid_endpoints(self, client):
        """Тест обработки неверных эндпоинтов"""
        # Тестируем несуществующий эндпоинт
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        
        # Тестируем неверный метод
        response = client.get("/api/save_order/")
        assert response.status_code == 405  # Method Not Allowed
        
        # Тестируем неверные данные
        response = client.post("/api/save_order/", json={"invalid": "data"})
        assert response.status_code == 422  # Unprocessable Entity
