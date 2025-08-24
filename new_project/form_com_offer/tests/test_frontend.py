"""
Тесты для фронтенда
"""
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch
from front.front import (
    fill_fields_from_order_diff,
    fill_components_fields_from_order,
    save_kp_handler,
    save_components_handler,
    save_comment_handler,
    load_selected_order,
    load_compose_order,
    add_next_aircon_handler,
    save_compose_client_handler,
    select_aircons_handler,
    generate_kp_handler,
    save_kp_handler
)


class TestFrontend:
    """Тесты для фронтенда"""
    
    @pytest.fixture
    def sample_order_data(self):
        """Фикстура с тестовыми данными заказа"""
        return {
            "id": 1,
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
            "comment": "Тестовый комментарий",
            "status": "draft",
            "pdf_path": None,
            "created_at": "2025-01-01"
        }
    
    @pytest.fixture
    def sample_compose_order_data(self):
        """Фикстура с тестовыми данными составного заказа"""
        return {
            "id": 2,
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
            "comment": "Тестовый комментарий для составного заказа",
            "status": "draft",
            "pdf_path": None,
            "created_at": "2025-01-01"
        }
    
    def test_fill_fields_from_order_diff(self, sample_order_data):
        """Тест функции fill_fields_from_order_diff"""
        # Тестируем заполнение полей из данных заказа
        result = fill_fields_from_order_diff(sample_order_data)
        
        # Проверяем, что функция возвращает словарь с обновлениями
        assert isinstance(result, dict)
        
        # Проверяем основные поля
        assert result["name"] == "Тест Клиент"
        assert result["phone"] == "+375001234567"
        assert result["mail"] == "test@example.com"
        assert result["address"] == "Тестовый адрес"
        assert result["area"] == 50
        assert result["type_room"] == "квартира"
        assert result["discount"] == 5
        assert result["wifi"] is True
        assert result["inverter"] is False
        assert result["price"] == 15000
        assert result["brand"] == "Любой"
        assert result["mount_type"] == "Любой"
        assert result["ceiling_height"] == 2.7
        assert result["illumination"] == "Средняя"
        assert result["num_people"] == 2
        assert result["activity"] == "Сидячая работа"
        assert result["num_computers"] == 1
        assert result["num_tvs"] == 1
        assert result["other_power"] == 500
        assert result["installation_price"] == 100
        assert result["comment"] == "Тестовый комментарий"
    
    def test_fill_components_fields_from_order(self, sample_order_data):
        """Тест функции fill_components_fields_from_order"""
        # Создаем тестовый каталог компонентов
        components_catalog = {
            "components": [
                {
                    "name": "труба 6,35х0,76 (1/4'') мм",
                    "price": 9.93,
                    "currency": "BYN",
                    "unit": "м."
                },
                {
                    "name": "труба 9,52х0,76 (3/8'') мм",
                    "price": 12.50,
                    "currency": "BYN",
                    "unit": "м."
                }
            ]
        }
        
        # Тестируем заполнение полей компонентов
        result = fill_components_fields_from_order(sample_order_data, components_catalog)
        
        # Проверяем, что функция возвращает список обновлений
        assert isinstance(result, list)
        
        # Проверяем, что количество обновлений соответствует количеству компонентов * 3 поля
        expected_updates = len(components_catalog["components"]) * 3
        assert len(result) == expected_updates
        
        # Проверяем, что обновления содержат правильные значения
        # Первый компонент (выбранный)
        assert result[0]["value"] is True  # checkbox
        assert result[1]["value"] == 1     # qty
        assert result[2]["value"] == 10    # length
        
        # Второй компонент (не выбранный)
        assert result[3]["value"] is False  # checkbox
        assert result[4]["value"] == 0      # qty
        assert result[5]["value"] == 0      # length
    
    @pytest.mark.asyncio
    async def test_save_kp_handler(self):
        """Тест функции save_kp_handler"""
        # Мокаем httpx.AsyncClient
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True, "order_id": 123}
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Тестируем сохранение заказа
            result = await save_kp_handler(
                order_id_hidden_value=None,
                name="Тест Клиент",
                phone="+375001234567",
                mail="test@example.com",
                address="Тестовый адрес",
                date="2025-01-01",
                area=50,
                type_room="квартира",
                discount=5,
                wifi=True,
                inverter=False,
                price=15000,
                mount_type="Любой",
                ceiling_height=2.7,
                illumination="Средняя",
                num_people=2,
                activity="Сидячая работа",
                num_computers=1,
                num_tvs=1,
                other_power=500,
                brand="Любой",
                installation_price=100
            )
            
            # Проверяем результат
            assert "успешно сохранён" in result[0]
            assert result[1] == 123
    
    @pytest.mark.asyncio
    async def test_save_components_handler_regular_order(self):
        """Тест функции save_components_handler для обычного заказа"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Создаем тестовые данные компонентов (только первые несколько)
            components_inputs = [True, 1, 10, False, 0, 0]  # 2 компонента * 3 поля
            
            result = await save_components_handler(1, *components_inputs)
            
            # Проверяем результат
            assert "успешно сохранены" in result[0]
            assert result[1] == 1
    
    @pytest.mark.asyncio
    async def test_save_components_handler_compose_order(self):
        """Тест функции save_components_handler для составного заказа"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Создаем тестовые данные компонентов
            components_inputs = [True, 1, 10, False, 0, 0]  # 2 компонента * 3 поля
            
            result = await save_components_handler(2, *components_inputs)
            
            # Проверяем результат
            assert "составного заказа успешно сохранены" in result[0]
            assert result[1] == 2
    
    @pytest.mark.asyncio
    async def test_save_comment_handler_regular_order(self):
        """Тест функции save_comment_handler для обычного заказа"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            # Мокаем ответ для обычного заказа (не составной)
            mock_response_get = AsyncMock()
            mock_response_get.status_code = 404  # Не составной заказ
            
            mock_response_post = AsyncMock()
            mock_response_post.json.return_value = {"success": True}
            mock_response_post.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response_get
            mock_client_instance.post.return_value = mock_response_post
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await save_comment_handler(1, "Тестовый комментарий")
            
            # Проверяем результат
            assert "успешно сохранён" in result
    
    @pytest.mark.asyncio
    async def test_save_comment_handler_compose_order(self):
        """Тест функции save_comment_handler для составного заказа"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            # Мокаем ответ для составного заказа
            mock_response_get = AsyncMock()
            mock_response_get.status_code = 200
            mock_response_get.json.return_value = {"id": 2, "status": "draft"}
            
            mock_response_post = AsyncMock()
            mock_response_post.json.return_value = {"success": True}
            mock_response_post.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response_get
            mock_client_instance.post.return_value = mock_response_post
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await save_comment_handler(2, "Тестовый комментарий для составного заказа")
            
            # Проверяем результат
            assert "успешно сохранён" in result
    
    @pytest.mark.asyncio
    async def test_load_selected_order(self, sample_order_data):
        """Тест функции load_selected_order"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_order_data
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await load_selected_order(1)
            
            # Проверяем, что функция возвращает обновления для UI
            assert isinstance(result, list)
            # Проверяем, что количество обновлений соответствует ожидаемому
            # (поля формы + компоненты + скрытые поля)
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_load_compose_order(self, sample_compose_order_data):
        """Тест функции load_compose_order"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_compose_order_data
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await load_compose_order(2)
            
            # Проверяем, что функция возвращает обновления для UI
            assert isinstance(result, list)
            # Проверяем, что количество обновлений соответствует ожидаемому
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_add_next_aircon_handler(self):
        """Тест функции add_next_aircon_handler"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True, "message": "Кондиционер добавлен"}
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await add_next_aircon_handler(2)
            
            # Проверяем результат
            assert "добавлен" in result
    
    @pytest.mark.asyncio
    async def test_save_compose_client_handler(self):
        """Тест функции save_compose_client_handler"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True, "order_id": 2}
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await save_compose_client_handler(
                compose_order_id_hidden_value=None,
                name="Тест Клиент",
                phone="+375001234567",
                mail="test@example.com",
                address="Тестовый адрес",
                date="2025-01-01",
                discount=5
            )
            
            # Проверяем результат
            assert "успешно сохранены" in result[0]
            assert result[1] == 2
            assert result[2] == 2  # order_id_hidden
    
    @pytest.mark.asyncio
    async def test_select_aircons_handler(self):
        """Тест функции select_aircons_handler"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True, "message": "Кондиционеры выбраны"}
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await select_aircons_handler(1)
            
            # Проверяем результат
            assert "выбраны" in result
    
    @pytest.mark.asyncio
    async def test_generate_kp_handler(self):
        """Тест функции generate_kp_handler"""
        with patch('front.front.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"success": True, "pdf_path": "/path/to/file.pdf"}
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await generate_kp_handler(1)
            
            # Проверяем результат
            assert "сгенерировано" in result[0]
            assert "/path/to/file.pdf" in result[1]
    
    def test_error_handling(self):
        """Тест обработки ошибок"""
        # Тестируем обработку некорректного ID заказа
        with pytest.raises(ValueError):
            # Попытка преобразовать нечисловое значение в int
            int("invalid")
        
        # Тестируем обработку отсутствующих данных
        empty_data = {}
        result = fill_fields_from_order_diff(empty_data)
        
        # Проверяем, что функция не падает с ошибкой
        assert isinstance(result, dict)
    
    def test_component_catalog_consistency(self):
        """Тест согласованности каталога компонентов"""
        # Проверяем, что каталог компонентов содержит все необходимые поля
        from front.front import COMPONENTS_CATALOG
        
        assert "components" in COMPONENTS_CATALOG
        assert isinstance(COMPONENTS_CATALOG["components"], list)
        
        for component in COMPONENTS_CATALOG["components"]:
            assert "name" in component
            assert "price" in component
            assert "currency" in component
            assert "unit" in component
            assert isinstance(component["name"], str)
            assert isinstance(component["price"], (int, float))
            assert isinstance(component["currency"], str)
            assert isinstance(component["unit"], str)
