import os
import fitz  # PyMuPDF
import json

# Путь к директории с файлами
base_path = 'C:/Users/Lenovo/Desktop/development/working_project/new_project/form_com_offer/docs'
pdf_path = os.path.join(base_path, 'air_catalogs')
images_path = os.path.join(base_path, 'images')

# Создаем папку для изображений, если её нет
os.makedirs(images_path, exist_ok=True)

def extract_pdf_data(pdf_file_path):
    """Извлекает текст и изображения из PDF файла"""
    print(f"Обрабатываем PDF файл: {pdf_file_path}")
    
    try:
        doc = fitz.open(pdf_file_path)
        pdf_data = {
            'file_name': os.path.basename(pdf_file_path),
            'pages': [],
            'text_content': '',
            'images': []
        }
        
        image_counter = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Извлекаем текст
            page_text = page.get_text()
            pdf_data['text_content'] += f"\\n--- Страница {page_num + 1} ---\\n" + page_text
            
            # Извлекаем изображения
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n < 5:  # Проверяем, что это не CMYK
                        img_filename = f"{os.path.splitext(os.path.basename(pdf_file_path))[0]}_img_{image_counter}.png"
                        img_path = os.path.join(images_path, img_filename)
                        
                        # Сохраняем изображение
                        pix.save(img_path)
                        
                        pdf_data['images'].append({
                            'filename': img_filename,
                            'path': img_path,
                            'page': page_num + 1,
                            'width': pix.width,
                            'height': pix.height
                        })
                        
                        image_counter += 1
                        print(f"  Сохранено изображение: {img_filename}")
                    
                    pix = None  # Освобождаем память
                    
                except Exception as e:
                    print(f"  Ошибка при извлечении изображения: {e}")
                    continue
        
        doc.close()
        return pdf_data
        
    except Exception as e:
        print(f"Ошибка при обработке PDF файла {pdf_file_path}: {e}")
        return None

# Обработка всех PDF файлов
all_pdf_data = []

for filename in os.listdir(pdf_path):
    if filename.endswith('.pdf'):
        full_path = os.path.join(pdf_path, filename)
        pdf_data = extract_pdf_data(full_path)
        if pdf_data:
            all_pdf_data.append(pdf_data)

print(f"Всего обработано PDF файлов: {len(all_pdf_data)}")

# Сохранение данных из PDF в файл JSON
pdf_output_path = os.path.join(base_path, 'pdf_data.json')
with open(pdf_output_path, 'w', encoding='utf-8') as f:
    json.dump(all_pdf_data, f, ensure_ascii=False, indent=4)

print(f"Данные из PDF сохранены в: {pdf_output_path}")
print(f"Изображения сохранены в папке: {images_path}")
