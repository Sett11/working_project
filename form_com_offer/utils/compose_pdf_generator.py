"""
Модуль генерации PDF-файлов коммерческих предложений для составных заказов.
Использует библиотеку reportlab для создания PDF-документов с несколькими кондиционерами.
"""
import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re
import asyncio
import json

from utils.mylogger import Logger
from utils.pdf_generator import FONTS_REGISTERED, FONT_NAME_NORMAL, FONT_NAME_BOLD

# Импортируем CRUD операции для работы со счетчиком КП
try:
    from db import crud
except ImportError:
    crud = None

logger = Logger("compose_pdf_generator", "compose_pdf_generator.log")


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
        
        logger.info(f"Генерация PDF КП для составного заказа. Клиент: {client_data.get('full_name', 'N/A')}")
        logger.info(f"Количество кондиционеров: {len(airs)}")
        
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
        file_name = f"КП_№ {current_offer_number}_от_{today_str}_{safe_full_name}_составной.pdf"
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
            ["Исполнитель:", "Бурак Дмитрий +375 44 55 123 44"],
            ["Тип помещения:", "Составной заказ (несколько помещений)"]
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
            room_type = order_params.get("room_type", f"Помещение #{i+1}")
            room_area = aircon_params.get("area", 0)
            
            # Заголовок для комнаты
            room_title = f"{room_type} ({room_area} м²)"
            story.append(Paragraph(room_title, styleVariantTitle))
            
            # Таблица кондиционеров для этой комнаты
            selected_aircons = aircon_result.get("selected_aircons", [])
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
                
                for ac in selected_aircons:  # Показываем все подобранные варианты
                    # Теперь ac - это словарь, а не объект модели
                    logger.info(f"Обрабатываем кондиционер: {ac}")
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
                    logger.info(f"Description для кондиционера: '{description}'")
                    if description:
                        specs_list.append(description)
                    
                    specs_text = ". ".join(specs_list)
                    logger.info(f"Итоговые характеристики: '{specs_text}'")
                    
                    # Убираем ограничение длины для полного отображения характеристик

                    # Получаем полное название без сокращений
                    name_text = ac.get('model_name', "") or ""
                    
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
                        Paragraph("шт.", styleTableCell),
                        Paragraph(str(qty), styleTableCell),
                        Paragraph(f"{price:.0f}" if price == int(price) else f"{price:.2f}", styleTableCell),
                        Paragraph(f"{discount:.2f}", styleTableCell),
                        Paragraph(f"{total_with_discount:.2f}", styleTableCell),
                        Paragraph("в наличии", styleTableCell)
                    ])
                
                ac_table = Table(
                    ac_table_data, 
                    colWidths=[40*mm, 36*mm, 50*mm, 10*mm, 10*mm, 12*mm, 14*mm, 18*mm, 16*mm],
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
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('WORDWRAP', (0,1), (-1,-1)),
                ]))
                story.append(ac_table)
                
                
                
                # Суммируем стоимость монтажа для каждого кондиционера
                installation_price_val = order_params.get('installation_price', 0)
                if installation_price_val is not None and installation_price_val != '':
                    try:
                        total_installation_price += float(installation_price_val)
                    except (ValueError, TypeError):
                        logger.error(f"Ошибка преобразования installation_price для комнаты {room_type}")
            
            story.append(Spacer(1, 15))

        # --- Таблица комплектующих (точно как в оригинале) ---
        total_components = 0
        logger.info(f"Компоненты для PDF: {components}")
        if components:
            story.append(Paragraph("Комплектующие и материалы:", styleBold))
            story.append(Spacer(1, 8))
            comp_table_data = [[
                Paragraph("Наименование", styleTableHeader),
                Paragraph("Ед. изм.", styleTableHeader),
                Paragraph("Кол-во", styleTableHeader),
                Paragraph("Цена за ед., BYN", styleTableHeader),
                Paragraph("Сумма, BYN", styleTableHeader)
            ]]
            
            for comp in components:
                logger.info(f"Обрабатываем компонент: {comp}")
                if comp.get("selected"):
                    price = float(comp.get('price', 0))
                    unit = comp.get('unit', 'шт.')
                    if unit == 'м.':
                        qty_or_length = int(comp.get('length', 0))
                    else:
                        qty_or_length = int(comp.get('qty', 0))
                    
                    total_without_discount = price * qty_or_length
                    total_components += total_without_discount
                    
                    comp_table_data.append([
                        Paragraph(comp.get('name', ''), styleTableCell),
                        Paragraph(unit, styleTableCell),
                        Paragraph(str(qty_or_length), styleTableCell),
                        Paragraph(f"{price:.2f}", styleTableCell),
                        Paragraph(f"{total_without_discount:.2f}", styleTableCell)
                    ])
            
            # Итоговая строка для комплектующих
            if len(comp_table_data) > 1:  # Есть выбранные комплектующие
                comp_table_data.append([
                    Paragraph("Итого", styleTableHeader),
                    '', '', '',
                    Paragraph(f"{total_components:.2f}", styleTableHeader)
                ])
                
                comp_table = Table(
                    comp_table_data, 
                    colWidths=[60*mm, 20*mm, 15*mm, 25*mm, 25*mm],
                    repeatRows=1
                )
                comp_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('FONTNAME', (0,0), (-1,0), FONT_NAME_NORMAL),
                    ('FONTNAME', (0,1), (-1,-1), FONT_NAME_NORMAL),
                    ('FONTSIZE', (0,0), (-1,-1), 7),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('ALIGN', (2,1), (2,-1), 'CENTER'),
                    ('ALIGN', (3,1), (4,-1), 'RIGHT'),
                    ('ALIGN', (0,0), (-1,0), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('SPAN', (0,-1), (3,-1)),
                    ('BACKGROUND', (0,-1), (-1,-1), colors.white),
                    ('FONTNAME', (0,-1), (-1,-1), FONT_NAME_NORMAL),
                ]))
                story.append(comp_table)
                story.append(Spacer(1, 15))

        # --- Блок работ (стоимость монтажа уже учтена в цикле выше) ---
        logger.info(f"Общая стоимость монтажа: {total_installation_price:.2f}")
        
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
            logger.info(f"Попытка добавить логотип в конец PDF для составного заказа. Путь: {end_logo_path}")
            if end_logo_path and os.path.exists(end_logo_path):
                logger.info(f"Логотип найден, добавляем в PDF: {end_logo_path}")
                end_logo = Image(end_logo_path, width=60*mm, height=40*mm)
                story.append(end_logo)
                story.append(Spacer(1, 10))
                logger.info("Логотип успешно добавлен в конец PDF для составного заказа")
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
