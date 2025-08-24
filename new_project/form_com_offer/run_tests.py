#!/usr/bin/env python3
"""
Скрипт для запуска тестов приложения
"""
import sys
import os
import subprocess
import argparse
from pathlib import Path

def run_command(command, description):
    """Выполняет команду и выводит результат"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Выполняется команда: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✅ {description} - УСПЕШНО")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - ОШИБКА")
        print(f"Код ошибки: {e.returncode}")
        return False

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    required_packages = [
        "pytest",
        "pytest-asyncio",
        "httpx",
        "fastapi",
        "sqlalchemy",
        "asyncpg",
        "reportlab",
        "gradio"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - НЕ УСТАНОВЛЕН")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Отсутствуют пакеты: {', '.join(missing_packages)}")
        print("Установите их командой:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ Все зависимости установлены")
    return True

def run_unit_tests():
    """Запускает модульные тесты"""
    return run_command(
        "python -m pytest tests/ -v -m 'not integration and not slow'",
        "Модульные тесты"
    )

def run_integration_tests():
    """Запускает интеграционные тесты"""
    return run_command(
        "python -m pytest tests/ -v -m integration",
        "Интеграционные тесты"
    )

def run_database_tests():
    """Запускает тесты базы данных"""
    return run_command(
        "python -m pytest tests/test_database.py -v",
        "Тесты базы данных"
    )

def run_api_tests():
    """Запускает тесты API"""
    return run_command(
        "python -m pytest tests/test_api.py -v",
        "Тесты API"
    )

def run_frontend_tests():
    """Запускает тесты фронтенда"""
    return run_command(
        "python -m pytest tests/test_frontend.py -v",
        "Тесты фронтенда"
    )

def run_pdf_tests():
    """Запускает тесты PDF генерации"""
    return run_command(
        "python -m pytest tests/test_pdf_generation.py -v",
        "Тесты PDF генерации"
    )

def run_all_tests():
    """Запускает все тесты"""
    return run_command(
        "python -m pytest tests/ -v",
        "Все тесты"
    )

def run_tests_with_coverage():
    """Запускает тесты с покрытием кода"""
    return run_command(
        "python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term",
        "Тесты с покрытием кода"
    )

def run_specific_test(test_path):
    """Запускает конкретный тест"""
    return run_command(
        f"python -m pytest {test_path} -v",
        f"Тест: {test_path}"
    )

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Запуск тестов приложения")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "database", "api", "frontend", "pdf", "all", "coverage"],
        default="all",
        help="Тип тестов для запуска"
    )
    parser.add_argument(
        "--test",
        help="Путь к конкретному тесту"
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Проверить зависимости"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Подробный вывод"
    )
    
    args = parser.parse_args()
    
    # Переходим в директорию проекта
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print("🧪 ТЕСТИРОВАНИЕ ПРИЛОЖЕНИЯ")
    print("="*60)
    
    # Проверяем зависимости, если нужно
    if args.check_deps:
        if not check_dependencies():
            sys.exit(1)
    
    # Запускаем тесты в зависимости от аргументов
    success = True
    
    if args.test:
        success = run_specific_test(args.test)
    elif args.type == "unit":
        success = run_unit_tests()
    elif args.type == "integration":
        success = run_integration_tests()
    elif args.type == "database":
        success = run_database_tests()
    elif args.type == "api":
        success = run_api_tests()
    elif args.type == "frontend":
        success = run_frontend_tests()
    elif args.type == "pdf":
        success = run_pdf_tests()
    elif args.type == "coverage":
        success = run_tests_with_coverage()
    else:  # all
        success = run_all_tests()
    
    # Выводим итоговый результат
    print(f"\n{'='*60}")
    if success:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✅ Приложение готово к использованию")
    else:
        print("💥 НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ!")
        print("❌ Требуется исправление ошибок")
    print(f"{'='*60}")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
