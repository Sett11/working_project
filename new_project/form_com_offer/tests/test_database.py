"""
Тесты для базы данных и CRUD операций
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_session, engine
from db import crud, models, schemas
import json
from datetime import date


class TestDatabase:
    """Тесты для базы данных"""
    
    @pytest.fixture
    async def db_session(self):
        """Фикстура для создания сессии базы данных"""
        async for session in get_session():
            yield session
            await session.rollback()
    
    @pytest.mark.asyncio
    async def test_create_client(self, db_session: AsyncSession):
        """Тест создания клиента"""
        client_data = schemas.ClientCreate(
            full_name="Тест Клиент",
            phone="+375001234567",
            email="test@example.com",
            address="Тестовый адрес"
        )
        
        client = await crud.create_client(db_session, client_data)
        
        assert client.id is not None
        assert client.full_name == "Тест Клиент"
        assert client.phone == "+375001234567"
        assert client.email == "test@example.com"
        assert client.address == "Тестовый адрес"
    
    @pytest.mark.asyncio
    async def test_get_client_by_phone(self, db_session: AsyncSession):
        """Тест получения клиента по телефону"""
        # Создаем клиента
        client_data = schemas.ClientCreate(
            full_name="Тест Клиент",
            phone="+375001234567",
            email="test@example.com",
            address="Тестовый адрес"
        )
        created_client = await crud.create_client(db_session, client_data)
        
        # Получаем клиента по телефону
        found_client = await crud.get_client_by_phone(db_session, "+375001234567")
        
        assert found_client is not None
        assert found_client.id == created_client.id
        assert found_client.full_name == "Тест Клиент"
    
    @pytest.mark.asyncio
    async def test_create_order(self, db_session: AsyncSession):
        """Тест создания заказа"""
        # Создаем клиента
        client_data = schemas.ClientCreate(
            full_name="Тест Клиент",
            phone="+375001234567",
            email="test@example.com",
            address="Тестовый адрес"
        )
        client = await crud.create_client(db_session, client_data)
        
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
        
        order_payload = schemas.OrderCreate(
            client_id=client.id,
            created_at=date.today(),
            status="draft",
            pdf_path=None,
            order_data=order_data
        )
        
        order = await crud.create_order(db_session, order_payload)
        
        assert order.id is not None
        assert order.client_id == client.id
        assert order.status == "draft"
        assert order.pdf_path is None
        
        # Проверяем, что данные заказа сохранились правильно
        saved_data = json.loads(order.order_data)
        assert saved_data["client_data"]["full_name"] == "Тест Клиент"
        assert saved_data["order_params"]["room_area"] == 50
        assert saved_data["aircon_params"]["wifi"] is True
        assert len(saved_data["components"]) == 1
        assert saved_data["components"][0]["name"] == "труба 6,35х0,76 (1/4'') мм"
        assert saved_data["comment"] == "Тестовый комментарий"
    
    @pytest.mark.asyncio
    async def test_create_compose_order(self, db_session: AsyncSession):
        """Тест создания составного заказа"""
        # Создаем клиента
        client_data = schemas.ClientCreate(
            full_name="Тест Клиент",
            phone="+375001234567",
            email="test@example.com",
            address="Тестовый адрес"
        )
        client = await crud.create_client(db_session, client_data)
        
        # Создаем составной заказ
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
        
        order_payload = schemas.ComposeOrderCreate(
            client_id=client.id,
            created_at=date.today(),
            status="draft",
            pdf_path=None,
            compose_order_data=compose_order_data
        )
        
        order = await crud.create_compose_order(db_session, order_payload)
        
        assert order.id is not None
        assert order.client_id == client.id
        assert order.status == "draft"
        assert order.pdf_path is None
        
        # Проверяем, что данные составного заказа сохранились правильно
        saved_data = json.loads(order.compose_order_data)
        assert saved_data["client_data"]["full_name"] == "Тест Клиент"
        assert saved_data["order_params"]["visit_date"] == "2025-01-01"
        assert len(saved_data["airs"]) == 1
        assert saved_data["airs"][0]["order_params"]["room_area"] == 50
        assert len(saved_data["components"]) == 1
        assert saved_data["components"][0]["name"] == "труба 6,35х0,76 (1/4'') мм"
        assert saved_data["comment"] == "Тестовый комментарий для составного заказа"
    
    @pytest.mark.asyncio
    async def test_get_orders_list(self, db_session: AsyncSession):
        """Тест получения списка заказов"""
        # Создаем клиента
        client_data = schemas.ClientCreate(
            full_name="Тест Клиент",
            phone="+375001234567",
            email="test@example.com",
            address="Тестовый адрес"
        )
        client = await crud.create_client(db_session, client_data)
        
        # Создаем обычный заказ
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
        
        order_payload = schemas.OrderCreate(
            client_id=client.id,
            created_at=date.today(),
            status="draft",
            pdf_path=None,
            order_data=order_data
        )
        
        order = await crud.create_order(db_session, order_payload)
        
        # Получаем список заказов
        orders = await crud.get_orders_list(db_session)
        
        assert len(orders) >= 1
        
        # Ищем наш заказ в списке
        found_order = None
        for o in orders:
            if o["id"] == order.id:
                found_order = o
                break
        
        assert found_order is not None
        assert found_order["client_name"] == "Тест Клиент"
        assert found_order["order_type"] == "Order"
        assert found_order["status"] == "draft"
    
    @pytest.mark.asyncio
    async def test_get_order_by_id(self, db_session: AsyncSession):
        """Тест получения заказа по ID"""
        # Создаем клиента
        client_data = schemas.ClientCreate(
            full_name="Тест Клиент",
            phone="+375001234567",
            email="test@example.com",
            address="Тестовый адрес"
        )
        client = await crud.create_client(db_session, client_data)
        
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
            "components": [],
            "comment": "Тестовый комментарий"
        }
        
        order_payload = schemas.OrderCreate(
            client_id=client.id,
            created_at=date.today(),
            status="draft",
            pdf_path=None,
            order_data=order_data
        )
        
        order = await crud.create_order(db_session, order_payload)
        
        # Получаем заказ по ID
        found_order = await crud.get_order_by_id(db_session, order.id)
        
        assert found_order is not None
        assert found_order.id == order.id
        assert found_order.client_id == client.id
        assert found_order.status == "draft"
        
        # Проверяем данные заказа
        saved_data = json.loads(found_order.order_data)
        assert saved_data["client_data"]["full_name"] == "Тест Клиент"
        assert saved_data["comment"] == "Тестовый комментарий"
    
    @pytest.mark.asyncio
    async def test_get_compose_order_by_id(self, db_session: AsyncSession):
        """Тест получения составного заказа по ID"""
        # Создаем клиента
        client_data = schemas.ClientCreate(
            full_name="Тест Клиент",
            phone="+375001234567",
            email="test@example.com",
            address="Тестовый адрес"
        )
        client = await crud.create_client(db_session, client_data)
        
        # Создаем составной заказ
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
            "components": [],
            "comment": "Тестовый комментарий для составного заказа"
        }
        
        order_payload = schemas.ComposeOrderCreate(
            client_id=client.id,
            created_at=date.today(),
            status="draft",
            pdf_path=None,
            compose_order_data=compose_order_data
        )
        
        order = await crud.create_compose_order(db_session, order_payload)
        
        # Получаем составной заказ по ID
        found_order = await crud.get_compose_order_by_id(db_session, order.id)
        
        assert found_order is not None
        assert found_order.id == order.id
        assert found_order.client_id == client.id
        assert found_order.status == "draft"
        
        # Проверяем данные составного заказа
        saved_data = json.loads(found_order.compose_order_data)
        assert saved_data["client_data"]["full_name"] == "Тест Клиент"
        assert len(saved_data["airs"]) == 1
        assert saved_data["comment"] == "Тестовый комментарий для составного заказа"
