import os
from datetime import datetime


def clear_logs():
    """Очистка файла логов"""
    if os.path.exists("logs.txt"):
        os.remove("logs.txt")
    with open("logs.txt", "w", encoding="utf-8") as f:
        f.write("=== Логи приложения ===\n")


def log_event(event_name: str, details: str = ""):
    """Запись события в лог-файл"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {event_name} {details}\n")