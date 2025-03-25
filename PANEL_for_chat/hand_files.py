from typing import List, Dict, Tuple
import os
from logs import log_event

# Хранилище данных
uploaded_files = {}


def process_uploaded_files(files: List[str]) -> str:
    """Обработка загруженных файлов"""
    file_info = []
    for file_path in files:
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / 1024  # KB
            file_info.append(f"{file_name} -> {file_size:.2f} KB")
            uploaded_files[file_name] = file_path
            log_event("FILE_PROCESS", f"Successfully processed: {file_name}")
        except Exception as e:
            log_event("ERROR", f"Failed to process file {file_path}: {str(e)}")
    return "\n".join(file_info) if file_info else "Нет загруженных файлов"


def clear_files_from_memory():
    """Очистка файлов из памяти"""
    for file_path in uploaded_files.values():
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            log_event("ERROR", f"Failed to delete file {file_path}: {str(e)}")
    uploaded_files.clear()


def handle_file_delete(files: List[str]) -> str:
    """Обработка удаления файла"""
    if not files:
        clear_files_from_memory()
        return "Нет загруженных файлов"
    
    current_files = {os.path.basename(f) for f in files}
    for file_name in list(uploaded_files.keys()):
        if file_name not in current_files:
            try:
                file_path = uploaded_files[file_name]
                if os.path.exists(file_path):
                    os.remove(file_path)
                del uploaded_files[file_name]
                log_event("FILE_DELETE", f"Deleted file: {file_name}")
            except Exception as e:
                log_event("ERROR", f"Failed to delete file {file_name}: {str(e)}")
    
    return update_file_display()


def update_file_display() -> str:
    """Обновление отображения списка файлов"""
    log_event("FILE_LIST_UPDATE", f"Current files: {list(uploaded_files.keys())}")
    file_info = []
    for file_name, file_path in uploaded_files.items():
        file_size = os.path.getsize(file_path) / 1024  # KB
        file_info.append(f"{file_name} -> {file_size:.2f} KB")
    return "\n".join(file_info) if file_info else "Нет загруженных файлов"


def update_file_display_sync(files: List[str]) -> str:
    """Синхронизированное обновление отображения файлов"""
    return process_uploaded_files(files) if files else "Нет загруженных файлов"


def handle_file_delete_sync(files: List[str]) -> str:
    """Синхронизированная обработка удаления файлов"""
    log_event("FILE_DELETE", files)
    return handle_file_delete(files)
