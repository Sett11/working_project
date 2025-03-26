import os
import io
from typing import Dict, List, Tuple, Optional, Union
import pdfplumber  # для работы с PDF
import docx  # python-docx для работы с DOCX
from pptx import Presentation  # python-pptx для работы с PPTX
from PIL import Image
from logs import log_event
from action_model import describe_image

# Максимальное количество символов для обработки
MAX_CHARS = 100000

def safe_extract_text(func):
    """Декоратор для безопасного извлечения текста с логированием ошибок"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_event("ERROR", f"Failed to extract text: {str(e)}")
            return "", []
    return wrapper

@safe_extract_text
def extract_text_from_txt(file_path: str) -> str:
    """Извлечение текста из TXT файлов"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

@safe_extract_text
def extract_text_from_pdf(file_path: str) -> Tuple[str, List[Image.Image]]:
    """Извлечение текста и изображений из PDF"""
    text = ""
    images = []
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # Извлекаем текст
            text += page.extract_text() or ""
            
            # Извлекаем изображения
            for image in page.images:
                try:
                    # Получаем изображение как bytes
                    image_bytes = image["stream"].get_data()
                    image = Image.open(io.BytesIO(image_bytes))
                    images.append(image)
                except Exception as e:
                    log_event("ERROR", f"Failed to process image from PDF: {str(e)}")
    
    return text, images

@safe_extract_text
def extract_text_from_docx(file_path: str) -> Tuple[str, List[Image.Image]]:
    """Извлечение текста и изображений из DOCX"""
    text = ""
    images = []
    
    doc = docx.Document(file_path)
    
    # Извлекаем текст из параграфов
    for para in doc.paragraphs:
        text += para.text + "\n"
    
    # Извлекаем текст из таблиц
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += cell.text + " "
            text += "\n"
    
    # Извлекаем изображения
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            try:
                image_data = rel.target_part.blob
                image = Image.open(io.BytesIO(image_data))
                images.append(image)
            except Exception as e:
                log_event("ERROR", f"Failed to process image from DOCX: {str(e)}")
    
    return text, images

@safe_extract_text
def extract_text_from_pptx(file_path: str) -> Tuple[str, List[Image.Image]]:
    """Извлечение текста и изображений из PPTX"""
    text = ""
    images = []
    
    prs = Presentation(file_path)
    
    for slide in prs.slides:
        for shape in slide.shapes:
            # Извлекаем текст из фигур
            if hasattr(shape, "text"):
                text += shape.text + "\n"
            
            # Извлекаем изображения
            if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                try:
                    image_stream = io.BytesIO(shape.image.blob)
                    image = Image.open(image_stream)
                    images.append(image)
                except Exception as e:
                    log_event("ERROR", f"Failed to process image from PPTX: {str(e)}")
    
    return text, images

def process_document(file_path: str) -> Dict[str, Union[str, bool]]:
    """Обрабатывает документ и извлекает из него текст и описания изображений"""
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Словарь соответствия расширений и функций обработки
    processors = {
        '.txt': (extract_text_from_txt, []),
        '.pdf': extract_text_from_pdf,
        '.docx': extract_text_from_docx,
        '.pptx': extract_text_from_pptx
    }
    
    try:
        if file_ext not in processors:
            log_event("WARNING", f"Unsupported file format: {file_ext}")
            return {
                "content": f"Неподдерживаемый формат файла: {file_ext}",
                "truncated": False
            }
        
        # Получаем функцию обработки и дополнительные аргументы
        processor, extra_args = processors[file_ext] if isinstance(processors[file_ext], tuple) else (processors[file_ext], [])
        
        # Обрабатываем документ
        text, images = processor(file_path, *extra_args)
        
        # Обрабатываем изображения
        image_descriptions = []
        for i, img in enumerate(images):
            description = describe_image(img)
            if description:
                image_descriptions.append(f"<text from image {i+1}>\n{description}\n</text from image {i+1}>")
        
        # Объединяем текст и описания изображений
        full_content = text + "\n\n" + "\n\n".join(image_descriptions)
        
        # Проверяем длину и при необходимости обрезаем
        if len(full_content) > MAX_CHARS:
            full_content = full_content[:MAX_CHARS]
            log_event("WARNING", f"Document {file_name} was truncated (exceeds {MAX_CHARS} chars)")
            return {
                "content": full_content,
                "truncated": True
            }
        
        return {
            "content": full_content,
            "truncated": False
        }
    except Exception as e:
        log_event("ERROR", f"Failed to process document {file_path}: {str(e)}")
        return {
            "content": f"Ошибка при обработке файла: {str(e)}",
            "truncated": False
        }

def get_formatted_documents_for_prompt(documents: Dict[str, str]) -> str:
    """Форматирует содержимое документов для вставки в промпт"""
    return "\n\n".join(f"<{doc_name}>\n{content}\n</{doc_name}>" for doc_name, content in documents.items())
