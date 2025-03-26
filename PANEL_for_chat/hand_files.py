from typing import List, Dict, Tuple, Optional, Any
import os
import shutil
import tempfile
from logs import log_event
from read_files import process_document, get_formatted_documents_for_prompt
from config import UPLOADS_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS

# Хранилище данных
uploaded_files = {}
processed_documents = {}  # Хранение обработанных документов: {"название файла": "содержимое"}

def is_safe_file(filename: str) -> bool:
    """Проверка безопасности файла"""
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def get_documents_status() -> str:
    """Получение статуса обработки документов"""
    docs = get_documents_content()
    total_chars = sum(len(content) for content in docs.values())
    
    if not docs:
        return "Нет загруженных документов."
    
    status = f"Обработано документов: {len(docs)}, общее количество символов: {total_chars}"
    if total_chars > 0:
        status += "\nДокументы готовы для запросов."
    return status


def process_uploaded_files(files: List[str]) -> str:
    """Обработка загруженных файлов"""
    file_info = []
    
    # Создаем директорию для загрузок, если не существует
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    
    for file_path in files:
        try:
            file_name = os.path.basename(file_path)
            
            # Проверяем безопасность файла
            if not is_safe_file(file_name):
                log_event("WARNING", f"Пропущен небезопасный файл: {file_name}")
                continue
                
            # Проверяем размер файла
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                log_event("WARNING", f"Файл слишком большой: {file_name}")
                continue
            
            # Копируем файл во временную директорию
            with tempfile.NamedTemporaryFile(delete=False, dir=UPLOADS_DIR) as temp_file:
                shutil.copy2(file_path, temp_file.name)
                dest_path = temp_file.name
            
            file_info.append(f"{file_name} -> {file_size/1024:.2f} KB")
            uploaded_files[file_name] = dest_path
            
            # Обрабатываем документ и извлекаем текст и описания изображений
            document_result = process_document(dest_path)
            processed_documents[file_name] = document_result["content"]
            
            # Добавляем информацию о результате обработки
            status = " (обрезано)" if document_result["truncated"] else ""
            file_info[-1] += status
            
            log_event("FILE_PROCESS", f"Successfully processed: {file_name}{status}")
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
    processed_documents.clear()

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
                
                if file_name in processed_documents:
                    del processed_documents[file_name]
                
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
        
        status = ""
        if file_name in processed_documents:
            content_len = len(processed_documents[file_name])
            status = f" (обработано, {content_len} символов)"
        
        file_info.append(f"{file_name} -> {file_size:.2f} KB{status}")
    return "\n".join(file_info) if file_info else "Нет загруженных файлов"


def get_documents_content() -> Dict[str, str]:
    """Возвращает словарь с обработанными документами"""
    return processed_documents


def get_documents_for_prompt() -> str:
    """Возвращает форматированный текст документов для вставки в промпт"""
    return get_formatted_documents_for_prompt(processed_documents)

def upload_and_update_status(files: List[str]) -> Tuple[str, str]:
    """Функция загрузки файлов с обновлением статуса"""
    file_display = process_uploaded_files(files)
    
    # Получаем информацию о документах
    docs = get_documents_content()
    total_chars = sum(len(content) for content in docs.values())
    
    status_text = f"Обработано документов: {len(docs)}, общее количество символов: {total_chars}"
    if total_chars > 0:
        status_text += "\nДокументы готовы для запросов."
    
    return file_display, status_text

def delete_and_update_status(files: List[str]) -> Tuple[str, str]:
    """Функция удаления файлов с обновлением статуса"""
    file_display = handle_file_delete(files)
    
    # Получаем информацию о документах
    docs = get_documents_content()
    total_chars = sum(len(content) for content in docs.values())
    
    status_text = f"Обработано документов: {len(docs)}, общее количество символов: {total_chars}"
    if not docs:
        status_text = "Нет загруженных документов."
    
    return file_display, status_text

def clear_all_files() -> Tuple[str, None, str]:
    """Очистка всех файлов"""
    file_display = handle_file_delete([])
    status_text = "Все файлы удалены. Загрузите новые документы для анализа."
    return file_display, None, status_text
