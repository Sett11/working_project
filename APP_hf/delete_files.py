import os
from logs import log_event as log_event_hf

def log_event(message):
    log_event_hf(f"FROM DELETE_FILES: {message}")

def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            log_event(f'Файл {file_path} удалён.')
    except Exception as e:
        log_event(f'Ошибка удаления файла {file_path}: {e}')