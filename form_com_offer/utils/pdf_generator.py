# utils/pdf_generator.py
"""
Модуль генерации PDF-файлов коммерческих предложений.
Использует библиотеку reportlab для создания PDF-документов.
"""
import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
# Импортируем registerFontFamily
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re
import asyncio

# Импортируем logger, предполагая, что он определен в utils.mylogger
# Если структура другая, нужно скорректировать импорт.
# Например, если файл mylogger.py находится в той же папке, что и pdf_generator.py:
# from .mylogger import Logger
# Для текущей структуры предположим, что mylogger.py в папке utils
from utils.mylogger import Logger

# Импортируем CRUD операции для работы со счетчиком КП
try:
    from db import crud
except ImportError:
    # Если импорт не удался, создаем заглушку
    crud = None

logger = Logger("pdf_generator", "pdf_generator.log")


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
        # Получаем базовую директорию проекта (папка form_com_offer)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Строим полный путь к изображению
        # Пример image_path_from_json: "images_airs/img_1.png"
        # Результат: /path/to/form_com_offer/docs/images_airs/img_1.png
        full_path = os.path.join(base_dir, 'docs', image_path_from_json)
        
        # Проверяем существование файла
        if os.path.exists(full_path):
            return full_path
        else:
            logger.warning(f"Изображение кондиционера не найдено: {full_path}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при получении изображения кондиционера для {image_path_from_json}: {e}")
        return None


def get_logo_path():
    """
    Получает полный путь к логотипу фирмы.
    
    Returns:
        str: Полный путь к логотипу или None, если файл не найден
    """
    try:
        # Получаем базовую директорию проекта (папка form_com_offer)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Строим полный путь к логотипу
        # Результат: /path/to/form_com_offer/utils/image_for_pdf/everis.png
        logo_path = os.path.join(base_dir, 'utils', 'image_for_pdf', 'everis.png')
        
        # Проверяем существование файла
        if os.path.exists(logo_path):
            return logo_path
        else:
            logger.warning(f"Логотип не найден: {logo_path}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при получении логотипа: {e}")
        return None


# --- Константы ---
# Порядковый номер КП теперь получается из базы данных

# --- Регистрация шрифтов ---
# Определяем пути к файлам шрифтов
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, 'fonts')
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

async def generate_commercial_offer_pdf(
    client_data: dict,
    order_params: dict,
    aircon_variants: list,
    components: list,
    discount_percent: float,
    offer_number: str = None,
    save_dir: str = "commercial_offer_pdf",
    db_session = None
) -> str:
    """
    Генерирует PDF-файл коммерческого предложения по заданным данным.
    Все значения, которые могут быть None, приводятся к строке для Paragraph.
    Логирует входные данные и ошибки.
    """
    logger.info(f"Генерация PDF КП. client_data={client_data}, order_params={order_params}, "
                f"aircon_variants={len(aircon_variants) if aircon_variants else 0}, "
                f"components={len(components) if components else 0}, discount_percent={discount_percent}, "
                f"offer_number={offer_number}")

    try:
        # Создаем директорию для сохранения
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
            fontName=FONT_NAME_NORMAL, # Используем базовое имя
            fontSize=16,
            alignment=1, # Center
            spaceAfter=12,
            # ВАЖНО: Используем bold=True, если шрифты зарегистрированы правильно
            bold=True if FONTS_REGISTERED else None # Для Helvetica-Bold это не нужно
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
            fontName=FONT_NAME_NORMAL, # Используем базовое имя
            bold=True if FONTS_REGISTERED else None # Активируем bold через флаг
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

        # --- Шапка документа ---
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
        
        # Обновленный заголовок с номером КП и полной датой (включая год)
        # Используем уже полученный номер КП
        story.append(Paragraph(f"КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ № {current_offer_number} {client_data.get('full_name', '')} от {today_str} г.", styleH))
        story.append(Spacer(1, 12))
        
        # --- Информация о клиенте и исполнителе ---
        client_info_data = [
            ["Заказчик:", client_data.get('full_name', '')],
            ["Адрес объекта:", client_data.get('address', '')],
            ["Телефон:", client_data.get('phone', '')],
            ["Исполнитель:", "Бурак Дмитрий +375 44 55 123 44"],
            ["Тип помещения:", order_params.get('room_type', '')]
        ]

        client_info_rows = []
        for label, value in client_info_data:
            client_info_rows.append([
                Paragraph(f"{label}", styleBold), # Используем styleBold для меток
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

        # --- Варианты кондиционеров ---
        for variant_idx, variant in enumerate(aircon_variants):
            # Заголовок варианта
            if variant.get('title'):
                story.append(Paragraph(variant['title'], styleVariantTitle))
            
            # Таблица кондиционеров для варианта
            if variant.get('items'):
                # Заголовки таблицы
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
                
                for ac in variant['items']:
                    price = float(ac.get('price', 0))
                    qty = int(ac.get('qty', 1))
                    discount = float(ac.get('discount_percent', 0))
                    total_with_discount = price * qty * (1 - discount / 100)
                    
                    # Формируем характеристики
                    specs_list = ac.get('specifications', [])
                    # Объединяем список в строку, заменяя переносы строк на пробелы или точки
                    specs_text = ". ".join([str(s).replace('\n', ' ') for s in specs_list if s])
                    
                    # Ограничиваем длину для предотвращения переполнения ячейки
                    if len(specs_text) > 300:
                        specs_text = specs_text[:297] + "..."

                    # Получаем полное название без сокращений
                    name_text = ac.get('name', '')
                    
                    # Получаем изображение кондиционера
                    image_path = get_aircon_image_path(ac.get('image_path'))
                    if image_path:
                        try:
                            # Создаем объект изображения с фиксированным размером
                            aircon_image = Image(image_path, width=30*mm, height=20*mm)
                        except Exception as e:
                            logger.error(f"Ошибка загрузки изображения {image_path}: {e}")
                            aircon_image = Paragraph("Нет фото", styleTableCell)
                    else:
                        aircon_image = Paragraph("Нет фото", styleTableCell)
                    
                    ac_table_data.append([
                        aircon_image,
                        Paragraph(name_text, styleTableCell),
                        Paragraph(specs_text, styleTableCell),
                        Paragraph(ac.get('unit', 'шт.'), styleTableCell),
                        Paragraph(str(qty), styleTableCell),
                        Paragraph(f"{price:.0f}" if price == int(price) else f"{price:.2f}", styleTableCell),
                        Paragraph(f"{discount:.2f}", styleTableCell),
                        Paragraph(f"{total_with_discount:.2f}", styleTableCell),
                        Paragraph("в наличии", styleTableCell)
                    ])
                
                ac_table = Table(
                    ac_table_data, 
                    colWidths=[40*mm, 36*mm, 50*mm, 10*mm, 10*mm, 12*mm, 14*mm, 18*mm, 16*mm],
                    repeatRows=1 # Повторять заголовок на новых страницах
                )
                ac_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('FONTNAME', (0,0), (-1,0), FONT_NAME_NORMAL),
                    ('FONTNAME', (0,1), (-1,-1), FONT_NAME_NORMAL),
                    ('FONTSIZE', (0,0), (-1,-1), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'), # По умолчанию выравнивание влево
                    ('ALIGN', (0,1), (0,-1), 'CENTER'), # Изображение - по центру
                    ('ALIGN', (3,1), (4,-1), 'CENTER'), # Ед.изм., Кол-во - по центру
                    ('ALIGN', (5,1), (7,-1), 'RIGHT'), # Цена, Скидка, Сумма - вправо
                    ('ALIGN', (8,1), (8,-1), 'CENTER'), # Галочка - по центру
                    ('ALIGN', (0,0), (-1,0), 'CENTER'), # Заголовки - по центру
                    ('VALIGN', (0,0), (-1,-1), 'TOP'), # Вертикальное выравнивание вверх
                    ('WORDWRAP', (0,1), (-1,-1)), # Перенос слов во всех ячейках данных
                ]))
                story.append(ac_table)
                story.append(Spacer(1, 15))

        # --- Таблица комплектующих ---
        total_components = 0
        if components:
            story.append(Paragraph("Комплектующие и материалы:", styleBold))
            story.append(Spacer(1, 8))
            comp_table_data = [[
                Paragraph("Наименование", styleTableHeader),
                Paragraph("Ед. изм.", styleTableHeader),
                Paragraph("Кол-во", styleTableHeader),
                Paragraph("Цена за ед., BYN", styleTableHeader),
                # Убран столбец "Скидка, %" для комплектующих
                Paragraph("Сумма, BYN", styleTableHeader)  # Убрано "с учетом скидки"
            ]]
            
            for comp in components:
                price = float(comp.get('price', 0))
                unit = comp.get('unit', 'шт.')
                if unit == 'м.':
                    qty_or_length = int(comp.get('length', 0))
                else:
                    qty_or_length = int(comp.get('qty', 0))
                
                # Убрана скидка для комплектующих - считаем полную стоимость
                total_without_discount = price * qty_or_length
                total_components += total_without_discount
                
                comp_table_data.append([
                    Paragraph(comp.get('name', ''), styleTableCell),
                    Paragraph(unit, styleTableCell),
                    Paragraph(str(qty_or_length), styleTableCell),
                    Paragraph(f"{price:.2f}", styleTableCell),
                    # Убран столбец скидки
                    Paragraph(f"{total_without_discount:.2f}", styleTableCell)  # Полная стоимость без скидки
                ])
            
            # Итоговая строка для комплектующих
            comp_table_data.append([
                Paragraph("Итого", styleTableHeader),
                '', '', '',
                Paragraph(f"{total_components:.2f}", styleTableHeader)
            ])
            
            comp_table = Table(
                comp_table_data, 
                colWidths=[60*mm, 20*mm, 15*mm, 25*mm, 25*mm],  # Уменьшено количество столбцов
                repeatRows=1
            )
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('FONTNAME', (0,0), (-1,0), FONT_NAME_NORMAL),
                ('FONTNAME', (0,1), (-1,-1), FONT_NAME_NORMAL),
                ('FONTSIZE', (0,0), (-1,-1), 7),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('ALIGN', (2,1), (2,-1), 'CENTER'), # Кол-во - по центру
                ('ALIGN', (3,1), (4,-1), 'RIGHT'), # Цена и Сумма - вправо
                ('ALIGN', (0,0), (-1,0), 'CENTER'), # Заголовки - по центру
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('SPAN', (0,-1), (3,-1)), # Объединяем ячейки для "Итого"
                ('BACKGROUND', (0,-1), (-1,-1), colors.white),
                # Применяем жирный шрифт к итоговой строке
                ('FONTNAME', (0,-1), (-1,-1), FONT_NAME_NORMAL),
                ('FONTNAME', (4,-1), (4,-1), FONT_NAME_NORMAL), # Или можно оставить тот же
                # Управление bold через стиль Paragraph, не через TableStyle
            ]))
            story.append(comp_table)
            story.append(Spacer(1, 15))

        # --- Блок работ ---
        installation_price = 0.0
        try:
            installation_price_val = order_params.get('installation_price', 0)
            # Обрабатываем возможные None или пустые строки
            if installation_price_val is not None and installation_price_val != '':
                installation_price = float(installation_price_val)
            else:
                installation_price = 0.0
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка преобразования installation_price '{order_params.get('installation_price')}': {e}")
            installation_price = 0.0
            
        logger.info(f"Стоимость работ (installation_price): {installation_price}")
        
        work_table_data = [
            [Paragraph("Монтажные работы", styleTableCell), Paragraph(f"{installation_price:.2f}", styleTableCell)]
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
        total_pay = total_components + installation_price
        
        # --- Итоговая сумма ---
        total_table = Table([
            [
                Paragraph(f"ИТОГО К ОПЛАТЕ:", styleBold),
                Paragraph(f"{total_pay:.2f} BYN", styleBold),
                Paragraph(f"+ стоимость выбранного кондиционера", styleTotalNote)
            ]
        ], colWidths=[80*mm, 50*mm, 70*mm])
        total_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT_NAME_NORMAL),
            ('FONTSIZE', (0,0), (1,0), 11), # Размер шрифта для основной суммы
            ('FONTSIZE', (2,0), (2,0), 9),  # Меньший размер для примечания
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
            ('LINEBELOW', (0,0), (1,0), 1, colors.black), # Линия под итогом
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(total_table)
        story.append(Spacer(1, 20))

        # --- Условия и примечания ---
        story.append(Paragraph("Условия поставки и монтажа:", styleBold))
        story.append(Paragraph("• Монтаж осуществляется в течение 3-5 рабочих дней после оплаты", styleSmall))
        story.append(Paragraph("• Гарантия на оборудование - 3 года, на монтажные работы - 2 года", styleSmall))
        story.append(Paragraph("• Цены указаны с учетом НДС", styleSmall))
        story.append(Spacer(1, 10))

        # --- Сохранение PDF ---
        doc.build(story)
        logger.info(f"PDF-файл '{file_path}' успешно сгенерирован.")
        return file_path

    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}", exc_info=True)
        raise

# --- Асинхронная обёртка для генерации PDF ---
async def generate_commercial_offer_pdf_async(*args, **kwargs):
    """
    Асинхронная обёртка для generate_commercial_offer_pdf.
    Теперь основная функция тоже асинхронная, поэтому просто передаем вызов.
    """
    return await generate_commercial_offer_pdf(*args, **kwargs)