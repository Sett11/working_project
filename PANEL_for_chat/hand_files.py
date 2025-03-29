from typing import List, Dict, Tuple
import os
import shutil
from logs import log_event
from read_files import process_document, get_formatted_documents_for_prompt
from config import UPLOADS_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, MAX_CHARS
import hashlib

# Хранилище данных
uploaded_files = {}
processed_documents = {}  # Хранение обработанных документов: {"название файла": "содержимое"}
mes = "Если Вы загружаете документы, то они будут обработаны и добавлены в контекст.\n\nНо дождитесь пока пропадёт это сообщение."

def is_safe_file(filename: str) -> bool:
    """Проверка безопасности файла"""
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def check_total_context_size(new_content: str) -> bool:
    """Проверка общего размера контекста"""
    current_total = sum(len(content) for content in processed_documents.values())
    new_total = current_total + len(new_content)
    return new_total <= MAX_CHARS

def get_documents_status() -> str:
    """Получение статуса обработки документов"""
    docs = get_documents_content()
    total_chars = sum(len(content) for content in docs.values())
    
    if not docs:
        return mes
    
    status = f"Обработано документов: {len(docs)}, общее количество символов: {total_chars}"
    if total_chars > 0:
        status += "\nДокументы готовы для запросов."
    return status

def get_file_hash(file_path: str) -> str:
    """Вычисляет хеш файла для проверки дубликатов"""
    hasher = hashlib.md5()  # Используем MD5 для создания хеша
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def process_uploaded_files(files: List[str]) -> str:
    """Обработка загруженных файлов"""
    file_info = []
    
    # Создаем директорию для загрузок, если не существует
    log_event("FILE_PROCESS", f"Creating uploads directory at: {UPLOADS_DIR}")
    try:
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        log_event("FILE_PROCESS", f"Uploads directory created/verified successfully")
    except Exception as e:
        log_event("ERROR", f"Failed to create uploads directory: {str(e)}")
        return f"Ошибка при создании директории для загрузок: {str(e)}"
    
    for file_path in files:
        try:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            log_event("FILE_PROCESS", f"Processing file: {file_name} with extension: {file_ext}")
            log_event("FILE_PROCESS", f"Source file path: {file_path}")
            
            # Проверяем безопасность файла
            if not is_safe_file(file_name):
                log_event("WARNING", f"Пропущен небезопасный файл: {file_name}")
                continue
                
            # Проверяем размер файла
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                log_event("WARNING", f"Файл слишком большой: {file_name}")
                continue
            
            # Вычисляем хеш файла
            file_hash = get_file_hash(file_path)
            # Проверяем, существует ли файл с таким же хешем
            existing_files = [f for f in os.listdir(UPLOADS_DIR) if f.endswith(file_ext)]
            if any(get_file_hash(os.path.join(UPLOADS_DIR, f)) == file_hash for f in existing_files):
                log_event("WARNING", f"Файл {file_name} уже загружен. Пропускаем.")
                continue
            
            # Копируем файл во временную директорию с сохранением расширения
            temp_name = os.path.join(UPLOADS_DIR, f"temp_{os.urandom(4).hex()}{file_ext}")
            log_event("FILE_PROCESS", f"Copying file to: {temp_name}")
            shutil.copy2(file_path, temp_name)
            dest_path = temp_name
            
            # Проверяем, что файл был успешно скопирован
            if not os.path.exists(dest_path):
                log_event("ERROR", f"File was not copied successfully to: {dest_path}")
                continue
                
            log_event("FILE_PROCESS", f"File copied successfully, size: {os.path.getsize(dest_path)} bytes")
            
            # Обрабатываем документ и извлекаем текст и описания изображений
            log_event("FILE_PROCESS", f"Starting document processing for: {file_name}")
            document_result = process_document(dest_path)
            
            # Проверяем общий размер контекста
            if not check_total_context_size(document_result["content"]):
                log_event("WARNING", f"Превышен максимальный размер контекста при загрузке файла: {file_name}")
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return "Размер контекста превышен!"
            
            file_info.append(f"{file_name} -> {file_size/1024:.2f} KB")
            uploaded_files[file_name] = dest_path
            processed_documents[file_name] = document_result["content"]
            
            # Добавляем информацию о результате обработки
            status = " (обрезано)" if document_result["truncated"] else ""
            file_info[-1] += status
            
            log_event("FILE_PROCESS", f"Successfully processed: {file_name}{status}")
            log_event("FILE_CONTENT", f"File {file_name} content length: {len(document_result['content'])}")
            log_event("FILE_CONTENT", f"File {file_name} first 200 chars: {document_result['content'][:200]}")
        except Exception as e:
            log_event("ERROR", f"Failed to process file {file_path}: {str(e)}")
            if 'dest_path' in locals() and os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception as del_e:
                    log_event("ERROR", f"Failed to delete temporary file {dest_path}: {str(del_e)}")
    return "\n".join(file_info) if file_info else mes


def clear_files_from_memory():
    """Очистка файлов из памяти"""
    try:
        for filename in os.listdir(UPLOADS_DIR):
            file_path = os.path.join(UPLOADS_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                log_event("FILE_DELETE", f"Deleted file: {filename}")
        log_event("FILE_DELETE", "All files in uploads directory have been deleted.")
    except Exception as e:
        log_event("ERROR", f"Failed to clear uploads directory: {str(e)}")
    uploaded_files.clear()
    processed_documents.clear()

def handle_file_delete(files: List[str]) -> str:
    """Обработка удаления файла"""
    if not files:
        clear_files_from_memory()
        return mes
    
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
    return "\n".join(file_info) if file_info else mes


def get_documents_content() -> Dict[str, str]:
    """Возвращает словарь с обработанными документами"""
    return processed_documents


def get_documents_for_prompt() -> str:
    """Возвращает форматированный текст документов для вставки в промпт"""
    formatted_text = get_formatted_documents_for_prompt(processed_documents)
    log_event("DOCUMENTS_CONTENT", f"Documents content length: {len(formatted_text)}")
    log_event("DOCUMENTS_CONTENT", f"First 500 chars: {formatted_text[:500]}")
    return formatted_text


def upload_and_update_status(files: List[str]) -> str:
    """Функция загрузки файлов с обновлением статуса"""
    process_uploaded_files(files)
    
    # Получаем информацию о документах
    docs = get_documents_content()
    total_chars = sum(len(content) for content in docs.values())
    
    status_text = f"Обработано документов: {len(docs)}, общее количество символов: {total_chars}"
    if total_chars > 0:
        status_text += "\nДокументы готовы для запросов."
    
    return status_text

def delete_and_update_status(files: List[str]) -> str:
    """Функция удаления файлов с обновлением статуса"""
    handle_file_delete(files)
    
    # Получаем информацию о документах
    docs = get_documents_content()
    total_chars = sum(len(content) for content in docs.values())
    
    status_text = f"Обработано документов: {len(docs)}, общее количество символов: {total_chars}"
    if not docs:
        status_text = mes
    
    return status_text

def clear_all_files() -> Tuple[None, str]:
    """Очистка всех файлов"""
    handle_file_delete([])
    status_text = "Все файлы удалены. Загрузите новые документы для анализа."
    return None, status_text