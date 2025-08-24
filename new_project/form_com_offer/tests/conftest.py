"""
Конфигурация pytest для тестирования
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройки для асинхронных тестов
@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для асинхронных тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Настройки для тестовой базы данных
@pytest.fixture(scope="session")
def test_database_url():
    """URL для тестовой базы данных"""
    return os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db")

# Настройки для логирования в тестах
@pytest.fixture(autouse=True)
def setup_logging():
    """Настройка логирования для тестов"""
    import logging
    
    # Настраиваем логирование для тестов
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Отключаем логи от внешних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

# Настройки для временных файлов
@pytest.fixture(scope="session")
def temp_dir():
    """Создает временную директорию для тестов"""
    import tempfile
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Очищаем временную директорию после тестов
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

# Настройки для моков
@pytest.fixture(autouse=True)
def setup_mocks():
    """Настройка моков для тестов"""
    # Здесь можно добавить глобальные моки, если потребуется
    pass

# Настройки для тестовых данных
@pytest.fixture
def sample_client_data():
    """Тестовые данные клиента"""
    return {
        "full_name": "Тест Клиент",
        "phone": "+375001234567",
        "email": "test@example.com",
        "address": "Тестовый адрес"
    }

@pytest.fixture
def sample_order_params():
    """Тестовые параметры заказа"""
    return {
        "room_area": 50,
        "room_type": "квартира",
        "discount": 5,
        "visit_date": "2025-01-01",
        "installation_price": 100
    }

@pytest.fixture
def sample_aircon_params():
    """Тестовые параметры кондиционера"""
    return {
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

@pytest.fixture
def sample_components():
    """Тестовые компоненты"""
    return [
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
    ]

# Настройки для маркеров pytest
def pytest_configure(config):
    """Настройка маркеров pytest"""
    config.addinivalue_line(
        "markers", "database: тесты, работающие с базой данных"
    )
    config.addinivalue_line(
        "markers", "api: тесты API эндпоинтов"
    )
    config.addinivalue_line(
        "markers", "frontend: тесты фронтенда"
    )
    config.addinivalue_line(
        "markers", "integration: интеграционные тесты"
    )
    config.addinivalue_line(
        "markers", "pdf: тесты генерации PDF"
    )
    config.addinivalue_line(
        "markers", "slow: медленные тесты"
    )

# Настройки для отчетов о тестах
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Вывод дополнительной информации после выполнения тестов"""
    print("\n" + "="*50)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*50)
    
    # Статистика по маркерам
    stats = terminalreporter.stats
    if stats:
        print("\nСтатистика по типам тестов:")
        for key, value in stats.items():
            print(f"  {key}: {len(value)} тестов")
    
    # Общая статистика
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    errors = len(terminalreporter.stats.get('error', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    
    print(f"\nОбщая статистика:")
    print(f"  Успешно: {passed}")
    print(f"  Провалено: {failed}")
    print(f"  Ошибки: {errors}")
    print(f"  Пропущено: {skipped}")
    
    total = passed + failed + errors + skipped
    if total > 0:
        success_rate = (passed / total) * 100
        print(f"  Процент успешности: {success_rate:.1f}%")
    
    print("="*50)

# Настройки для пропуска тестов
def pytest_collection_modifyitems(config, items):
    """Модификация коллекции тестов"""
    # Пропускаем тесты, если не установлены зависимости
    skip_markers = []
    
    try:
        import httpx
    except ImportError:
        skip_markers.append("httpx")
    
    try:
        import reportlab
    except ImportError:
        skip_markers.append("reportlab")
    
    try:
        import sqlalchemy
    except ImportError:
        skip_markers.append("sqlalchemy")
    
    for item in items:
        for marker in skip_markers:
            if marker in item.keywords:
                item.add_marker(pytest.mark.skip(reason=f"Требуется {marker}"))
