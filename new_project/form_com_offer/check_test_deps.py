#!/usr/bin/env python3
"""
Скрипт для проверки наличия всех необходимых зависимостей для тестирования
"""

import importlib
import sys

def check_dependency(module_name, package_name=None):
    """Проверяет, установлен ли модуль"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {package_name or module_name} - установлен")
        return True
    except ImportError:
        print(f"❌ {package_name or module_name} - НЕ установлен")
        return False

def main():
    """Основная функция проверки зависимостей"""
    print("🔍 Проверка зависимостей для тестирования...")
    print("=" * 50)
    
    # Основные зависимости для тестирования
    test_dependencies = [
        ("pytest", "pytest"),
        ("pytest_asyncio", "pytest-asyncio"),
        ("pytest_cov", "pytest-cov"),
        ("pytest_mock", "pytest-mock"),
        ("pytest_xdist", "pytest-xdist"),
        ("pytest_html", "pytest-html"),
        ("pytest_json_report", "pytest-json-report"),
        ("httpx", "httpx"),
        ("aiofiles", "aiofiles"),
    ]
    
    # Дополнительные зависимости приложения
    app_dependencies = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("gradio", "gradio"),
        ("sqlalchemy", "SQLAlchemy"),
        ("asyncpg", "asyncpg"),
        ("reportlab", "reportlab"),
        ("pydantic", "pydantic"),
    ]
    
    print("\n📦 Зависимости для тестирования:")
    test_missing = []
    for module, package in test_dependencies:
        if not check_dependency(module, package):
            test_missing.append(package)
    
    print("\n🔧 Зависимости приложения:")
    app_missing = []
    for module, package in app_dependencies:
        if not check_dependency(module, package):
            app_missing.append(package)
    
    print("\n" + "=" * 50)
    
    if test_missing or app_missing:
        print("❌ Обнаружены отсутствующие зависимости!")
        
        if test_missing:
            print(f"\n📋 Отсутствуют зависимости для тестирования:")
            for dep in test_missing:
                print(f"   - {dep}")
            print(f"\n💡 Установите их командой:")
            print(f"   pip install {' '.join(test_missing)}")
        
        if app_missing:
            print(f"\n📋 Отсутствуют зависимости приложения:")
            for dep in app_missing:
                print(f"   - {dep}")
            print(f"\n💡 Установите их командой:")
            print(f"   pip install {' '.join(app_missing)}")
        
        print(f"\n🐳 Или пересоберите Docker контейнеры:")
        print(f"   docker-compose down")
        print(f"   docker-compose build --no-cache")
        print(f"   docker-compose up -d")
        
        return False
    else:
        print("✅ Все зависимости установлены!")
        print("🚀 Можно запускать тесты:")
        print("   docker-compose exec backend python run_tests.py --all")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
