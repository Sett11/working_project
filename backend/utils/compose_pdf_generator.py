"""
Модуль генерации PDF-файлов коммерческих предложений для составных заказов.
Использует библиотеку reportlab для создания PDF-документов с несколькими кондиционерами.
"""
import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re
import json

from utils.mylogger import Logger

# Импортируем CRUD операции для работы со счетчиком КП
from sqlalchemy import select
from db import models
try:
    from db import crud
except ImportError:
    crud = None

logger = Logger("compose_pdf_generator", "compose_pdf_generator.log")

# --- Регистрация шрифтов ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE_DIR, 'utils', 'fonts')
FONT_PATH = os.path.join(FONT_DIR, 'arial.ttf')
FONT_BOLD_PATH = os.path.join(FONT_DIR, 'arialbd.ttf')

# Инициализируем флаг успешной регистрации
FONTS_REGISTERED = False

try:
    # Проверяем существование файлов шрифтов
    if not os.path.exists(FONT_PATH):
        logger.error(f"Файл шрифта {FONT_PATH} не найден! Скопируйте arial.ttf из C:/Windows/Fonts.")
    elif not os.path.exists(FONT_BOLD_PATH):
        logger.error(f"Файл жирного шрифта {FONT_BOLD_PATH} не найден! Скопируйте arialbd.ttf из C:/Windows/Fonts.")
    else:
        # Регистрируем шрифты
        pdfmetrics.registerFont(TTFont('Arial', FONT_PATH))
        pdfmetrics.registerFont(TTFont('Arial-Bold', FONT_BOLD_PATH))
        
        # Регистрируем семейство шрифтов - КЛЮЧЕВОЙ МОМЕНТ
        pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold')
        
        FONTS_REGISTERED = True
        logger.info("Шрифты Arial успешно зарегистрированы.")
        
except Exception as e:
    logger.error(f"Ошибка при регистрации шрифтов: {e}")

# Определяем имена шрифтов для использования в стилях
if FONTS_REGISTERED:
    FONT_NAME_NORMAL = 'Arial'
    FONT_NAME_BOLD = 'Arial' # Используем семейство + bold=True
else:
    # Fallback на встроенные шрифты, если Arial не зарегистрирован
    logger.warning("Используются встроенные шрифты Helvetica как fallback.")
    FONT_NAME_NORMAL = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'
# --- Конец регистрации шрифтов ---

async def find_aircon_by_model_name(model_name: str, db_session):
    """
    Ищет кондиционер в базе данных по имени модели.
    
    Args:
        model_name (str): Имя модели кондиционера (например, "EACS-18HSM/N3")
        db_session: Сессия базы данных
        
    Returns:
        dict: Данные кондиционера или None если не найден
    """
    try:
        if not db_session:
            logger.error("Сессия БД не передана для поиска кондиционера")
            return None
            
        # Ищем кондиционер по имени модели
        result = await db_session.execute(
            select(models.AirConditioner).filter(models.AirConditioner.model_name == model_name)
        )
        aircon = result.scalars().first()
        
        if aircon:
            logger.info(f"Найден кондиционер в БД: {aircon.brand} {aircon.model_name}")
            return {
                'brand': aircon.brand,
                'model_name': aircon.model_name,
                'cooling_power_kw': aircon.cooling_power_kw,
                'retail_price_byn': aircon.retail_price_byn,
                'image_path': aircon.image_path,
                'energy_efficiency_class': aircon.energy_efficiency_class,
                'description': aircon.description,
                'is_inverter': aircon.is_inverter,
                'has_wifi': aircon.has_wifi,
                'mount_type': aircon.mount_type,
                'series': aircon.series
            }
        else:
            logger.warning(f"Кондиционер с моделью '{model_name}' не найден в БД")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при поиске кондиционера '{model_name}' в БД: {e}")
        return None

def extract_model_name_from_string(aircon_string: str) -> str:
    """
    Извлекает имя модели из строки формата "Бренд | имя модели | мощность в квт | стоимость"
    
    Args:
        aircon_string (str): Строка с данными кондиционера
        
    Returns:
        str: Имя модели или пустая строка если не удалось извлечь
    """
    try:
        # Разделяем строку по " | "
        parts = aircon_string.split(" | ")
        if len(parts) >= 2:
            model_name = parts[1].strip()  # Второй элемент - имя модели
            logger.info(f"Извлечено имя модели: '{model_name}' из строки: '{aircon_string}'")
            return model_name
        else:
            logger.error(f"Не удалось извлечь имя модели из строки: '{aircon_string}'")
            return ""
    except Exception as e:
        logger.error(f"Ошибка при извлечении имени модели из строки '{aircon_string}': {e}")
        return ""


def get_aircon_image_path(image_path_from_json):
    """
    Получает полный путь к изображению кондиционера.
    
    Args:
        image_path_from_json (str): Путь к изображению из JSON (например, "images_airs/img_1.png")
        
    Returns:
        str: Полный путь к изображению или None, если файл не найден
    """
    if not image_path_from_json:
        return None
    
    try:
        # Получаем корневую директорию проекта (на уровень выше backend/)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        
        # Строим полный путь к изображению
        # Пример image_path_from_json: "images_airs/img_1.png"
        # Результат: /path/to/project_root/db/docs/images_airs/img_1.png
        full_path = os.path.join(project_root, 'db', 'docs', image_path_from_json)
        
        # Проверяем существование файла
        if os.path.exists(full_path):
            return full_path
        else:
            logger.warning(f"Изображение кондиционера не найдено: {full_path}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при получении изображения кондиционера для {image_path_from_json}: {e}")
        return None


def get_logo_path(filename="everis.png"):
    """
    Получает полный путь к логотипу фирмы.
    
    Args:
        filename (str): Имя файла логотипа (по умолчанию "everis.png")
    
    Returns:
        str: Полный путь к логотипу или None, если файл не найден
    """
    try:
        # Получаем базовую директорию проекта (папка form_com_offer)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Строим полный путь к логотипу
        # Результат: /path/to/form_com_offer/utils/image_for_pdf/{filename}
        logo_path = os.path.join(base_dir, 'utils', 'image_for_pdf', filename)
        
        # Проверяем существование файла
        if os.path.exists(logo_path):
            return logo_path
        else:
            logger.warning(f"Логотип не найден: {logo_path}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при получении логотипа: {e}")
        return None

async def generate_compose_commercial_offer_pdf(
    compose_order_data: dict,
    aircon_results: dict,
    components: list,
    discount_percent: float,
    offer_number: str = None,
    save_dir: str = "commercial_offer_pdf",
    db_session = None
) -> str:
    """
    Генерирует PDF-файл коммерческого предложения для составного заказа.
    
    Args:
        compose_order_data (dict): Данные составного заказа
        aircon_results (dict): Результаты подбора кондиционеров
        components (list): Список комплектующих
        discount_percent (float): Процент скидки
        offer_number (str): Номер КП
        save_dir (str): Директория для сохранения
        db_session: Сессия базы данных
        
    Returns:
        str: Путь к сгенерированному PDF файлу
    """
    try:
        client_data = compose_order_data.get("client_data", {})
        airs = compose_order_data.get("airs", [])
        rooms = compose_order_data.get("rooms", [])
        
        logger.info(f"Генерация PDF КП для составного заказа. Клиент: {client_data.get('full_name', 'N/A')}")
        logger.info(f"Количество кондиционеров: {len(airs)}")
        logger.info(f"Количество помещений: {len(rooms)}")
        
        # Создаем директорию если не существует
        abs_save_dir = os.path.abspath(save_dir)
        os.makedirs(abs_save_dir, exist_ok=True)
        
        # Формируем имя файла с полной датой (включая год)
        today = datetime.date.today()
        today_str = today.strftime("%d_%m_%Y")
        safe_full_name = re.sub(r'[^\w]', '_', client_data.get('full_name',''))
        
        # Получаем номер КП из базы данных или используем fallback
        current_offer_number = 1  # Fallback значение
        if db_session and crud:
            try:
                current_offer_number = await crud.increment_offer_counter(db_session)
                logger.info(f"Получен номер КП из БД: {current_offer_number}")
            except Exception as e:
                logger.error(f"Ошибка при получении номера КП из БД: {e}")
                current_offer_number = 1
        else:
            logger.warning("Сессия БД не передана или CRUD недоступен, используется fallback номер")
        
        # Формируем имя файла с номером КП
        file_name = f"КП_№ {current_offer_number}_от_{today_str}_{safe_full_name}.pdf"
        file_path = os.path.join(abs_save_dir, file_name)
        logger.info(f"Сформировано имя файла: {file_name}")
        
        # --- Стили документа ---
        styles = getSampleStyleSheet()
        
        # Создаем стили с учетом зарегистрированных шрифтов
        styleH = ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontName=FONT_NAME_NORMAL,
            fontSize=16,
            alignment=1, # Center
            spaceAfter=12,
            bold=True if FONTS_REGISTERED else None
        )
        
        styleN = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=FONT_NAME_NORMAL,
            fontSize=11,
            spaceAfter=6
        )
        
        styleBold = ParagraphStyle(
            'CustomBold',
            parent=styleN,
            fontName=FONT_NAME_NORMAL,
            bold=True if FONTS_REGISTERED else None
        )
        
        styleTableHeader = ParagraphStyle(
            'CustomTableHeader',
            parent=styles['Normal'],
            fontName=FONT_NAME_NORMAL,
            fontSize=8,
            alignment=1, # Center
            spaceAfter=3,
            bold=True if FONTS_REGISTERED else None
        )
        
        styleTableCell = ParagraphStyle(
            'CustomTableCell',
            parent=styles['Normal'],
            fontName=FONT_NAME_NORMAL,
            fontSize=7,
            spaceAfter=3
        )
        
        styleSmall = ParagraphStyle(
            'CustomSmall',
            parent=styles['Normal'],
            fontName=FONT_NAME_NORMAL,
            fontSize=8,
            spaceAfter=3
        )
        
        styleVariantTitle = ParagraphStyle(
            'CustomVariantTitle',
            parent=styles['Heading2'],
            fontName=FONT_NAME_NORMAL,
            fontSize=12,
            spaceAfter=6,
            bold=True if FONTS_REGISTERED else None
        )
        
        styleVariantDesc = ParagraphStyle(
            'CustomVariantDesc',
            parent=styles['Normal'],
            fontName=FONT_NAME_NORMAL,
            fontSize=10,
            spaceAfter=6
        )
        
        styleTotalNote = ParagraphStyle(
            'CustomTotalNote',
            parent=styles['Normal'],
            fontName=FONT_NAME_NORMAL,
            fontSize=9,
            spaceAfter=0,
            spaceBefore=0,
            bold=True if FONTS_REGISTERED else None
        )
        # --- Конец стилей ---

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=10*mm,
            bottomMargin=15*mm
        )
        story = []

        # --- Шапка документа (точно как в оригинале) ---
        # Добавляем логотип фирмы
        logo_path = get_logo_path()
        if logo_path:
            try:
                logo = Image(logo_path, width=30*mm, height=20*mm)
                story.append(logo)
                story.append(Spacer(1, 5))
            except Exception as e:
                logger.error(f"Ошибка загрузки логотипа: {e}")
        
        story.append(Paragraph("ООО «Эвериз Сервис»", styleBold))
        story.append(Paragraph("г. Минск, ул. Орловская, 40, пом. 25б, 220030", styleN))
        story.append(Paragraph("УНП 192812488", styleN))
        story.append(Paragraph("BY29 MTBK 3012 0001 0933 0013 0402", styleN))
        story.append(Paragraph("в ЗАО «МТБанк», БИК MTBKBY22", styleN))
        story.append(Spacer(1, 10))
        
        # Заголовок с номером КП и полной датой
        story.append(Paragraph(f"КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ № {current_offer_number} {client_data.get('full_name', '')} от {today_str} г.", styleH))
        story.append(Spacer(1, 12))
        
        # --- Информация о клиенте и исполнителе (точно как в оригинале) ---
        client_info_data = [
            ["Заказчик:", client_data.get('full_name', '')],
            ["Адрес объекта:", client_data.get('address', '')],
            ["Телефон:", client_data.get('phone', '')],
            ["Исполнитель:", "Бурак Дмитрий +375 44 55 123 44"]
        ]

        client_info_rows = []
        for label, value in client_info_data:
            client_info_rows.append([
                Paragraph(f"{label}", styleBold),
                Paragraph(str(value or ''), styleN)
            ])

        if client_data.get('email'):
            client_info_rows.insert(3, [
                Paragraph("Email:", styleBold),
                Paragraph(str(client_data.get('email')), styleN)
            ])

        # Создаем таблицу
        client_table = Table(client_info_rows, colWidths=[40*mm, 140*mm])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME_NORMAL),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(client_table)
        story.append(Spacer(1, 15))

        # --- Варианты кондиционеров для каждой комнаты ---
        total_installation_price = 0
        
        for i, aircon_result in enumerate(aircon_results.get("aircon_results", [])):
            # Получаем данные о комнате
            aircon_params = aircon_result.get("aircon_params", {})
            order_params = aircon_result.get("order_params", {})
            
            # Получаем тип помещения и площадь из данных помещения
            if i < len(rooms):
                room_type = rooms[i].get("room_type", f"Помещение #{i+1}")
                room_area = rooms[i].get("area", aircon_params.get("area", 0))
            else:
                room_type = f"Помещение #{i+1}"
            room_area = aircon_params.get("area", 0)
            
            # Заголовок для комнаты
            room_title = f"{room_type} ({room_area} м²)"
            story.append(Paragraph(room_title, styleVariantTitle))
            
            # Таблица кондиционеров для этой комнаты
            selected_aircons = aircon_result.get("selected_aircons", [])
            logger.info(f"Помещение {i+1}: найдено {len(selected_aircons)} кондиционеров")
            if selected_aircons:
                # Заголовки таблицы (точно как в оригинале)
                ac_table_data = [[
                    Paragraph("Изображение", styleTableHeader),
                    Paragraph("Наименование товара", styleTableHeader),
                    Paragraph("Характеристики", styleTableHeader),
                    Paragraph("Ед. изм.", styleTableHeader),
                    Paragraph("Кол-во", styleTableHeader),
                    Paragraph("Цена за ед., BYN", styleTableHeader),
                    Paragraph("Скидка %", styleTableHeader),
                    Paragraph("Сумма с учетом скидки, BYN", styleTableHeader),
                    Paragraph("Срок\nпоставки", styleTableHeader)
                ]]
                
                for ac_string in selected_aircons:  # Показываем все подобранные варианты
                    # Если это строка - извлекаем имя модели и ищем в БД
                    if isinstance(ac_string, str):
                        logger.info(f"Обрабатываем строку кондиционера: {ac_string}")
                        model_name = extract_model_name_from_string(ac_string)
                        if not model_name:
                            logger.error(f"Не удалось извлечь имя модели из строки: {ac_string}")
                            continue
                            
                        # Ищем кондиционер в БД по имени модели
                        ac = await find_aircon_by_model_name(model_name, db_session)
                        if not ac:
                            logger.error(f"Кондиционер с моделью '{model_name}' не найден в БД")
                            continue
                    elif isinstance(ac_string, dict):
                        # Если уже словарь - используем как есть
                        ac = ac_string
                    else:
                        logger.error(f"Неизвестный тип элемента selected_aircons: {type(ac_string)}")
                        continue
                    
                    # Теперь ac - это словарь, а не объект модели
                    # logger.info(f"Обрабатываем кондиционер: {ac}")  # Убрано избыточное логирование
                    price = float(ac.get('retail_price_byn', 0) or 0)
                    qty = 1
                    discount = float(discount_percent or 0)
                    total_with_discount = price * qty * (1 - discount / 100)
                    
                    # Формируем характеристики как в обычном КП
                    specs_list = []
                    
                    # 1. Бренд (добавляем первым)
                    brand = ac.get('brand', '')
                    if brand:
                        specs_list.append(brand)
                    
                    # 2. Мощность охлаждения
                    if ac.get('cooling_power_kw'):
                        specs_list.append(f"Охлаждение: {ac['cooling_power_kw']:.2f} кВт")
                    
                    # 3. Полное описание модели (description) - основная информация
                    description = ac.get('description', '')
                    # logger.info(f"Description для кондиционера: '{description}'")  # Убрано избыточное логирование
                    if description:
                        specs_list.append(description)
                    
                    specs_text = ". ".join(specs_list)
                    # logger.info(f"Итоговые характеристики: '{specs_text}'")  # Убрано избыточное логирование
                    
                    # Убираем ограничение длины для полного отображения характеристик

                    # Получаем полное название без сокращений
                    name_text = ac.get('model_name', "") or ""
                    
                    # Получаем изображение кондиционера
                    image_path = get_aircon_image_path(ac.get('image_path'))
                    if image_path:
                        try:
                            # Создаем объект изображения с принудительным ограничением размеров
                            aircon_image = Image(image_path, width=25*mm, height=20*mm)
                            # Принудительно изменяем размер изображения, игнорируя пропорции
                            aircon_image.drawWidth = 25*mm
                            aircon_image.drawHeight = 20*mm
                        except Exception as e:
                            logger.error(f"Ошибка загрузки изображения {image_path}: {e}")
                            aircon_image = Paragraph("Нет фото", styleTableCell)
                    else:
                        aircon_image = Paragraph("Нет фото", styleTableCell)
                    
                    ac_table_data.append([
                        aircon_image,
                        Paragraph(name_text, styleTableCell),
                        Paragraph(specs_text, styleTableCell),
                        Paragraph("шт.", styleTableCell),
                        Paragraph(str(qty), styleTableCell),
                        Paragraph(f"{price:.0f}" if price == int(price) else f"{price:.2f}", styleTableCell),
                        Paragraph(f"{discount:.2f}", styleTableCell),
                        Paragraph(f"{total_with_discount:.2f}", styleTableCell),
                        Paragraph("в наличии", styleTableCell)
                    ])
                
                ac_table = Table(
                    ac_table_data, 
                    colWidths=[30*mm, 29*mm, 47*mm, 10*mm, 10*mm, 12*mm, 14*mm, 17*mm, 16*mm],
                    repeatRows=1
                )
                ac_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('FONTNAME', (0,0), (-1,0), FONT_NAME_NORMAL),
                    ('FONTNAME', (0,1), (-1,-1), FONT_NAME_NORMAL),
                    ('FONTSIZE', (0,0), (-1,-1), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('ALIGN', (0,1), (0,-1), 'CENTER'), # Изображение - по центру
                    ('ALIGN', (3,1), (4,-1), 'CENTER'), # Ед.изм., Кол-во - по центру
                    ('ALIGN', (5,1), (7,-1), 'RIGHT'), # Цена, Скидка, Сумма - вправо
                    ('ALIGN', (8,1), (8,-1), 'CENTER'), # Галочка - по центру
                    ('ALIGN', (0,0), (-1,0), 'CENTER'),
                    ('ALIGN', (6,0), (6,0), 'LEFT'), # Заголовок "Скидка %" - по левому краю
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('WORDWRAP', (0,1), (-1,-1)),
                ]))
                story.append(ac_table)
                
                # Добавляем отступ между таблицами разных комнат (кроме последней)
                if i < len(aircon_results.get("aircon_results", [])) - 1:
                    story.append(Spacer(1, 15))
                
                # Суммируем стоимость монтажа из данных помещения
                if i < len(rooms):
                    installation_price_val = rooms[i].get('installation_price', 0)
                if installation_price_val is not None and installation_price_val != '':
                    try:
                        total_installation_price += float(installation_price_val)
                        logger.info(f"Добавлена стоимость монтажа для помещения {i+1}: {installation_price_val}")
                    except (ValueError, TypeError):
                        logger.error(f"Ошибка преобразования installation_price для помещения {i+1}: {installation_price_val}")
                else:
                    logger.warning(f"Нет данных о помещении {i+1} для получения стоимости монтажа")
                
                # --- Комплектующие для этого помещения ---
                if i < len(rooms):
                    room_components = rooms[i].get('components_for_room', [])
                    if room_components:
                        story.append(Paragraph(f"Комплектующие для помещения: {room_type}", styleBold))
                        story.append(Spacer(1, 8))
                        
                        room_comp_table_data = [[
                Paragraph("Наименование", styleTableHeader),
                Paragraph("Ед. изм.", styleTableHeader),
                Paragraph("Кол-во", styleTableHeader),
                Paragraph("Цена за ед., BYN", styleTableHeader),
                Paragraph("Сумма, BYN", styleTableHeader)
            ]]
            
            room_components_total = 0
            logger.info(f"Обрабатываем {len(room_components)} комплектующих для помещения {i+1}")
            for comp_idx, comp in enumerate(room_components):
                logger.info(f"Комплектующая {comp_idx+1}: {comp.get('name', 'Без названия')}, selected={comp.get('selected')}, price={comp.get('price', 0)}")
                if comp.get("selected"):
                    price = float(comp.get('price', 0))
                    unit = comp.get('unit', 'шт.')
                    if unit == 'м.':
                        qty_or_length = int(comp.get('length', 0))
                    else:
                        qty_or_length = int(comp.get('qty', 0))
                    
                    total_without_discount = price * qty_or_length
                    room_components_total += total_without_discount
                    logger.info(f"Добавлена комплектующая: {comp.get('name')} - {price} x {qty_or_length} = {total_without_discount}")
                    
                    room_comp_table_data.append([
                        Paragraph(comp.get('name', ''), styleTableCell),
                        Paragraph(unit, styleTableCell),
                        Paragraph(str(qty_or_length), styleTableCell),
                        Paragraph(f"{price:.2f}", styleTableCell),
                        Paragraph(f"{total_without_discount:.2f}", styleTableCell)
                    ])
            
            # Итоговая строка для комплектующих этого помещения
            if len(room_comp_table_data) > 1:
                room_comp_table_data.append([
                    Paragraph("Итого по помещению", styleTableHeader),
                    '', '', '',
                    Paragraph(f"{room_components_total:.2f}", styleTableHeader)
                ])
                
                room_comp_table = Table(
                    room_comp_table_data, 
                    colWidths=[4*cm, 2*cm, 2*cm, 3*cm, 3*cm]
                )
                room_comp_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('FONTNAME', (0,0), (-1,0), FONT_NAME_BOLD),
                    ('FONTNAME', (0,1), (-1,-1), FONT_NAME_NORMAL),
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('ALIGN', (2,1), (2,-1), 'CENTER'),
                    ('ALIGN', (3,1), (4,-1), 'RIGHT'),
                    ('ALIGN', (0,0), (-1,0), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('SPAN', (0,-1), (3,-1)),
                    ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
                    ('FONTNAME', (0,-1), (-1,-1), FONT_NAME_BOLD),
                ]))
                story.append(room_comp_table)
                story.append(Spacer(1, 15))
                
                logger.info(f"Добавлены комплектующие для помещения {i+1}: {room_components_total:.2f} BYN")
            
            story.append(Spacer(1, 15))

        # --- ИТОГОВАЯ СВОДКА ПО ВСЕМ ПОМЕЩЕНИЯМ ---
        # ЗАКОММЕНТИРОВАНО: Итоговая таблица комплектующих по всем помещениям
        # story.append(Paragraph("ИТОГОВАЯ СВОДКА", styleBold))
        # story.append(Spacer(1, 8))
        # 
        # # Собираем все комплектующие из всех помещений для итоговой таблицы
        # all_components_summary = {}
        # total_components = 0
        # 
        # logger.info(f"Формируем итоговую сводку по {len(rooms)} помещениям")
        # for i, room in enumerate(rooms):
        #     room_components = room.get('components_for_room', [])
        #     logger.info(f"Помещение {i+1}: {len(room_components)} комплектующих")
        #     for comp in room_components:
        #         if comp.get("selected"):
        #             comp_name = comp.get('name', '')
        #             price = float(comp.get('price', 0))
        #             unit = comp.get('unit', 'шт.')
        #             
        #             if unit == 'м.':
        #                 qty_or_length = int(comp.get('length', 0))
        #             else:
        #                 qty_or_length = int(comp.get('qty', 0))
        #             
        #             total_without_discount = price * qty_or_length
        #             total_components += total_without_discount
        #             logger.info(f"Итоговая сводка: {comp_name} - {price} x {qty_or_length} = {total_without_discount}")
        #             
        #             # Суммируем одинаковые комплектующие
        #             if comp_name in all_components_summary:
        #                 all_components_summary[comp_name]['qty'] += qty_or_length
        #                 all_components_summary[comp_name]['total'] += total_without_discount
        #             else:
        #                 all_components_summary[comp_name] = {
        #                     'unit': unit,
        #                     'price': price,
        #                     'qty': qty_or_length,
        #                     'total': total_without_discount
        #                 }
        # 
        # # Создаем итоговую таблицу комплектующих
        # if all_components_summary:
        #     summary_table_data = [[
        #         Paragraph("Наименование", styleTableHeader),
        #         Paragraph("Ед. изм.", styleTableHeader),
        #         Paragraph("Общее кол-во", styleTableHeader),
        #         Paragraph("Цена за ед., BYN", styleTableHeader),
        #         Paragraph("Общая сумма, BYN", styleTableHeader)
        #     ]]
        #     
        #     for comp_name, comp_data in all_components_summary.items():
        #         summary_table_data.append([
        #             Paragraph(comp_name, styleTableCell),
        #             Paragraph(comp_data['unit'], styleTableCell),
        #             Paragraph(str(comp_data['qty']), styleTableCell),
        #             Paragraph(f"{comp_data['price']:.2f}", styleTableCell),
        #             Paragraph(f"{comp_data['total']:.2f}", styleTableCell)
        #         ])
        #     
        #     # Итоговая строка
        #     summary_table_data.append([
        #         Paragraph("ИТОГО КОМПЛЕКТУЮЩИЕ", styleTableHeader),
        #             '', '', '',
        #             Paragraph(f"{total_components:.2f}", styleTableHeader)
        #         ])
        #         
        #     summary_table = Table(
        #         summary_table_data, 
        #             colWidths=[60*mm, 20*mm, 15*mm, 25*mm, 25*mm],
        #             repeatRows=1
        #         )
        #     summary_table.setStyle(TableStyle([
        #             ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        #         ('FONTNAME', (0,0), (-1,0), FONT_NAME_BOLD),
        #             ('FONTNAME', (0,1), (-1,-1), FONT_NAME_NORMAL),
        #             ('FONTSIZE', (0,0), (-1,-1), 7),
        #             ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        #             ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        #             ('ALIGN', (2,1), (2,-1), 'CENTER'),
        #             ('ALIGN', (3,1), (4,-1), 'RIGHT'),
        #             ('ALIGN', (0,0), (-1,0), 'CENTER'),
        #             ('VALIGN', (0,0), (-1,-1), 'TOP'),
        #             ('SPAN', (0,-1), (3,-1)),
        #         ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        #         ('FONTNAME', (0,-1), (-1,-1), FONT_NAME_BOLD),
        #         ]))
        #     story.append(summary_table)
        #     story.append(Spacer(1, 15))

        # --- Блок работ (стоимость монтажа уже учтена в цикле выше) ---
        # logger.info(f"Общая стоимость монтажа: {total_installation_price:.2f}")  # Убрано избыточное логирование
        
        # Отображаем общую стоимость монтажа
        if total_installation_price > 0:
            work_table_data = [
                [Paragraph("Монтажные работы (общая стоимость)", styleTableCell), Paragraph(f"{total_installation_price:.2f}", styleTableCell)]
            ]
            work_table = Table(
                work_table_data, 
                colWidths=[140*mm, 30*mm]
            )
            work_table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), FONT_NAME_NORMAL),
                ('FONTSIZE', (0,0), (-1,-1), 7),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ALIGN', (0,0), (0,0), 'LEFT'),
                ('ALIGN', (1,0), (1,0), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(work_table)
            story.append(Spacer(1, 15))

        # --- Расчет итоговой суммы ---
        # Итоговая сумма = комплектующие + монтаж (кондиционеры НЕ включаются)
        # Рассчитываем общую стоимость комплектующих из всех помещений
        total_components = 0
        for i, room in enumerate(rooms):
            room_components = room.get('components_for_room', [])
            for comp in room_components:
                if comp.get("selected"):
                    price = float(comp.get('price', 0))
                    unit = comp.get('unit', 'шт.')
                    
                    if unit == 'м.':
                        qty_or_length = int(comp.get('length', 0))
                    else:
                        qty_or_length = int(comp.get('qty', 0))
                    
                    total_without_discount = price * qty_or_length
                    total_components += total_without_discount
        
        total_pay = total_components + total_installation_price
        
        # --- Итоговая сумма ---
        total_table = Table([
            [
                Paragraph(f"ИТОГО К ОПЛАТЕ:", styleBold),
                Paragraph(f"{total_pay:.2f} BYN", styleBold),
                Paragraph(f"+ стоимость выбранных кондиционеров", styleTotalNote)
            ]
        ], colWidths=[80*mm, 50*mm, 70*mm])
        total_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT_NAME_NORMAL),
            ('FONTSIZE', (0,0), (1,0), 11),
            ('FONTSIZE', (2,0), (2,0), 9),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
            ('LINEBELOW', (0,0), (1,0), 1, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(total_table)
        
        
        
        story.append(Spacer(1, 20))

        # --- Условия и примечания (точно как в оригинале) ---
        story.append(Paragraph("Условия поставки и монтажа:", styleBold))
        story.append(Paragraph("• Монтаж осуществляется в течение 3-5 рабочих дней после оплаты", styleSmall))
        story.append(Paragraph("• Гарантия на оборудование - 3 года, на монтажные работы - 2 года", styleSmall))
        story.append(Paragraph("• Цены указаны с учетом НДС", styleSmall))
        story.append(Spacer(1, 10))

        # --- Логотип в конце документа ---
        story.append(Spacer(1, 20))
        try:
            end_logo_path = get_logo_path("everis_2.png")
            # logger.info(f"Попытка добавить логотип в конец PDF для составного заказа. Путь: {end_logo_path}")  # Убрано избыточное логирование
            if end_logo_path and os.path.exists(end_logo_path):
                # logger.info(f"Логотип найден, добавляем в PDF: {end_logo_path}")  # Убрано избыточное логирование
                end_logo = Image(end_logo_path, width=60*mm, height=40*mm)
                story.append(end_logo)
                story.append(Spacer(1, 10))
                # logger.info("Логотип успешно добавлен в конец PDF для составного заказа")  # Убрано избыточное логирование
            else:
                logger.warning(f"Логотип не найден или путь пустой: {end_logo_path}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении логотипа в конец PDF для составного заказа: {e}", exc_info=True)

        # --- Сохранение PDF ---
        doc.build(story)
        logger.info(f"PDF для составного заказа успешно сгенерирован: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF для составного заказа: {e}", exc_info=True)
        raise
