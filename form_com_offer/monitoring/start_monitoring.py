"""
Скрипт для запуска системы мониторинга с Grafana
"""
import asyncio
import subprocess
import sys
import os
from pathlib import Path

def run_command(command_list, description):
    """Выполняет команду и выводит результат"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command_list, check=True, capture_output=True, text=True)
        print(f"✅ {description} выполнено успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при {description.lower()}: {e}")
        print(f"Вывод: {e.stdout}")
        print(f"Ошибка: {e.stderr}")
        return False

def check_docker():
    """Проверяет, установлен ли Docker"""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_docker_compose():
    """Проверяет, установлен ли Docker Compose"""
    try:
        subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def main():
    """Основная функция запуска мониторинга"""
    print("🚀 Запуск системы мониторинга с Grafana")
    print("=" * 50)
    
    # Проверяем зависимости
    print("📋 Проверка зависимостей...")
    
    if not check_docker():
        print("❌ Docker не установлен. Установите Docker и попробуйте снова.")
        return False
    
    if not check_docker_compose():
        print("❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова.")
        return False
    
    print("✅ Docker и Docker Compose установлены")
    
    # Проверяем, что мы в правильной директории
    current_dir = Path.cwd()
    if not (current_dir / "monitoring" / "monitoring-compose.yml").exists():
        print("❌ Файл monitoring/monitoring-compose.yml не найден. Запустите скрипт из корневой директории проекта.")
        return False
    
    # Останавливаем существующие контейнеры мониторинга
    print("\n🛑 Остановка существующих контейнеров мониторинга...")
    run_command(["docker-compose", "-f", "monitoring/monitoring-compose.yml", "down"], "Остановка контейнеров")
    
    # Проверяем наличие .env файла
    env_file = Path("monitoring/.env")
    if not env_file.exists():
        print("\n⚠️  ВНИМАНИЕ: Файл monitoring/.env не найден!")
        print("   Рекомендуется создать файл .env с безопасным паролем:")
        print("   1. Скопируйте: cp monitoring/env.example monitoring/.env")
        print("   2. Установите безопасный пароль в файле .env")
        print("   3. Перезапустите скрипт")
        print("   Используется пароль по умолчанию (небезопасно для продакшена)")
    
    # Запускаем систему мониторинга
    print("\n🚀 Запуск системы мониторинга...")
    command = ["docker-compose", "-f", "monitoring/monitoring-compose.yml"]
    if env_file.exists():
        command.extend(["--env-file", str(env_file)])
    command.extend(["up", "-d"])
    if not run_command(command, "Запуск контейнеров мониторинга"):
        return False
    
    # Ждем немного для запуска сервисов
    print("\n⏳ Ожидание запуска сервисов...")
    import time
    time.sleep(10)
    
    # Проверяем статус контейнеров
    print("\n📊 Проверка статуса контейнеров...")
    run_command(["docker-compose", "-f", "monitoring/monitoring-compose.yml", "ps"], "Проверка статуса")
    
    print("\n" + "=" * 50)
    print("🎉 Система мониторинга запущена!")
    print("\n📱 Доступные сервисы:")
    print("   • Grafana: http://localhost:3000")
    print("     Логин: admin")
    if env_file.exists():
        print("     Пароль: настроен в файле .env")
    else:
        print("     Пароль: admin123 (небезопасно - настройте .env файл)")
    print("   • Prometheus: http://localhost:9090")
    print("   • Экспортер метрик: http://localhost:9091")
    
    print("\n📋 Следующие шаги:")
    print("   1. Откройте Grafana: http://localhost:3000")
    if env_file.exists():
        print("   2. Войдите с логином admin и паролем из файла .env")
    else:
        print("   2. Войдите с логином admin / admin123 (рекомендуется настроить .env)")
    print("   3. Дашборд 'AirCon Application Monitoring' должен быть доступен автоматически")
    print("   4. Убедитесь, что ваше приложение запущено на порту 8001")
    
    print("\n🛑 Для остановки мониторинга выполните:")
    print("   docker-compose -f monitoring/monitoring-compose.yml down")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
