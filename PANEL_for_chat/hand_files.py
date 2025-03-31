from typing import List, Dict, Tuple
import os
import shutil
from logs import log_event
from read_files import process_document
from config import UPLOADS_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, MAX_CHARS
import hashlib

# Хранилище данных
uploaded_files = {}  # {"название файла": "оригинальное_имя.расширение"}
processed_documents = {}  # {"название файла": "содержимое"}
file_hashes = {}  # {"название файла": "md5_хеш"}
mes = "Ваши документы загружаются, они будут обработаны и добавлены в контекст.\n\nДождитесь, пожалуйста, пока пропадёт это сообщение."

def is_safe_file(filename: str) -> bool:
    """Проверка безопасности файла по расширению"""
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def check_total_context_size(new_content: str) -> bool:
    """Проверка общего размера контекста"""
    current_total = sum(len(content) for content in processed_documents.values())
    return (current_total + len(new_content)) <= MAX_CHARS

def get_documents_status() -> str:
    """Статус обработки документов"""
    if not processed_documents:
        return mes
    total_chars = sum(len(content) for content in processed_documents.values())
    return f"Обработано документов: {len(processed_documents)}, символов: {total_chars}"

def get_file_hash(file_path: str) -> str:
    """Вычисляет MD5 хеш файла"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def process_uploaded_files(files: List[str]) -> str:
    """Основная функция обработки загруженных файлов"""
    if not files:
        return mes
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    processed_files = []
    for file_path in files:
        temp_path = None  # Инициализация переменной для временного пути
        try:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            # Проверки безопасности
            if not is_safe_file(file_name):
                log_event("WARNING", f"Небезопасный файл: {file_name}")
                continue
            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                log_event("WARNING", f"Файл слишком большой: {file_name}")
                continue
            # Проверка дубликатов по хешу
            file_hash = get_file_hash(file_path)
            if file_hash in file_hashes.values():
                log_event("WARNING", f"Дубликат файла: {file_name}")
                continue
            # Временное сохранение для обработки
            temp_path = os.path.join(UPLOADS_DIR, f"temp_{os.urandom(4).hex()}{file_ext}")
            shutil.copy2(file_path, temp_path)
            # Обработка документа
            doc_result = process_document(temp_path)
            if not check_total_context_size(doc_result["content"]):
                return "Превышен максимальный размер контекста!"
            # Сохраняем данные и удаляем временный файл
            uploaded_files[file_name] = file_name  # Сохраняем оригинальное имя
            processed_documents[file_name] = doc_result["content"]
            file_hashes[file_name] = file_hash
            status = " (обрезано)" if doc_result["truncated"] else ""
            processed_files.append(f"{file_name}{status}")
            log_event("FILE_PROCESS", f"Обработан: {file_name}{status}")
        except Exception as e:
            log_event("ERROR", f"Ошибка обработки {file_path}: {str(e)}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)  # Удаляем временный файл в любом случае
    return "\n".join(processed_files) if processed_files else mes

def clear_files_from_memory():
    """Полная очистка всех данных"""
    uploaded_files.clear()
    processed_documents.clear()
    file_hashes.clear()
    log_event("CLEANUP", "Все данные о файлах очищены")

def handle_file_delete(files: List[str]) -> str:
    """Удаление указанных файлов"""
    if not files:
        clear_files_from_memory()
        return mes
    for file_name in list(uploaded_files.keys()):
        if file_name not in files:
            uploaded_files.pop(file_name, None)
            processed_documents.pop(file_name, None)
            file_hashes.pop(file_name, None)
            log_event("FILE_DELETE", f"Удалён файл: {file_name}")
    return update_file_display()

def update_file_display() -> str:
    """Обновлённый вывод списка файлов (без доступа к UPLOADS_DIR)"""
    file_info = []
    for file_name in uploaded_files:
        content_len = len(processed_documents.get(file_name, ""))
        file_info.append(f"{file_name} ({content_len} символов)")
    return "\n".join(file_info) if file_info else mes

def get_documents_content() -> Dict[str, str]:
    """Возвращает обработанные документы"""
    return processed_documents

def get_formatted_documents_for_prompt() -> str:
    """Форматирует содержимое документов для вставки в промпт"""
    return "\n\n".join(f"<{doc_name}>\n{content}\n</{doc_name}>" for doc_name, content in processed_documents.items())

def upload_and_update_status(files: List[str]) -> str:
    """Обёртка для загрузки с обновлением статуса"""
    process_uploaded_files(files)
    return get_documents_status()

def delete_and_update_status(files: List[str]) -> str:
    """Обёртка для удаления с обновлением статуса"""
    handle_file_delete(files)
    return get_documents_status()

def clear_all_files() -> Tuple[None, str]:
    """Полная очистка"""
    clear_files_from_memory()
    return None, "Все файлы удалены. Загрузите новые документы."