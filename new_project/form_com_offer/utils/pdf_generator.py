"""
Модуль генерации PDF-файлов коммерческих предложений.
Использует библиотеку reportlab для создания PDF-документов.
"""
import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from utils.mylogger import Logger
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import re
import asyncio

logger = Logger("pdf_generator", "pdf_generator.log")

# Регистрация шрифтов
FONT_PATH = os.path.join(os.path.dirname(__file__), 'fonts', 'arial.ttf')
FONT_BOLD_PATH = os.path.join(os.path.dirname(__file__), 'fonts', 'arialbd.ttf')

if not os.path.exists(FONT_PATH):
    logger.error(f"Файл шрифта {FONT_PATH} не найден! Скопируйте arial.ttf из C:/Windows/Fonts.")
else:
    pdfmetrics.registerFont(TTFont('Arial', FONT_PATH))

if not os.path.exists(FONT_BOLD_PATH):
    logger.error(f"Файл жирного шрифта {FONT_BOLD_PATH} не найден! Скопируйте arialbd.ttf из C:/Windows/Fonts.")
else:
    pdfmetrics.registerFont(TTFont('Arial-Bold', FONT_BOLD_PATH))

def generate_commercial_offer_pdf(
    client_data: dict,
    order_params: dict,
    aircon_variants: list,  # Изменено на варианты кондиционеров
    components: list,
    discount_percent: float,
    offer_number: str = None,
    save_dir: str = "commercial_offer_pdf"
) -> str:
    """
    Генерирует PDF-файл коммерческого предложения по заданным данным.
    Все значения, которые могут быть None, приводятся к строке для Paragraph/split.
    Логирует входные данные и ошибки.
    """
    logger.info(f"Генерация PDF КП. client_data={client_data}, order_params={order_params}, aircon_variants={aircon_variants}, components={components}, discount_percent={discount_percent}, offer_number={offer_number}")
    try:
        # Создаем директорию для сохранения
        abs_save_dir = os.path.abspath(save_dir)
        os.makedirs(abs_save_dir, exist_ok=True)

        # Формируем имя файла
        today = datetime.date.today().strftime("%d_%m")
        safe_full_name = re.sub(r'[^\w]', '_', client_data.get('full_name',''))[:20]
        offer_number = offer_number or f"{today}_{safe_full_name}"
        file_name = f"КП_{offer_number}.pdf"
        file_path = os.path.join(abs_save_dir, file_name)

        # Стили документа
        styles = getSampleStyleSheet()
        styleH = ParagraphStyle('Heading1', parent=styles['Heading1'], fontName='Arial-Bold', fontSize=16, alignment=1)
        styleN = ParagraphStyle('Normal', parent=styles['Normal'], fontName='Arial', fontSize=11)
        styleBold = ParagraphStyle('Bold', parent=styleN, fontName='Arial-Bold')
        styleTableHeader = ParagraphStyle('TableHeader', parent=styles['Normal'], alignment=1, fontSize=9, fontName='Arial-Bold')
        styleTableCell = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=9, fontName='Arial')
        styleSmall = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, fontName='Arial')
        styleVariantTitle = ParagraphStyle('VariantTitle', parent=styles['Heading2'], fontName='Arial-Bold', fontSize=12, spaceAfter=6)
        styleVariantDesc = ParagraphStyle('VariantDesc', parent=styles['Normal'], fontName='Arial', fontSize=10, spaceAfter=12)

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
        story.append(Paragraph("ООО «Эвериз Сервис»", styleBold))
        story.append(Paragraph("г. Минск, ул. Орловская, 40, пом. 25б, 220030", styleN))  # Исправлен адрес
        story.append(Paragraph("УНП 192812488", styleN))
        story.append(Paragraph("BY29 MTBK 3012 0001 0933 0013 0402", styleN))
        story.append(Paragraph("в ЗАО «МТБанк», БИК MTBKBY22", styleN))
        story.append(Spacer(1, 10))
        
        # Обновленный заголовок с номером КП
        story.append(Paragraph(f"<b>КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ № {offer_number} от {today}г.</b>", styleH))
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
                Paragraph(f"<b>{label}</b>", styleN), 
                Paragraph(str(value or ''), styleN)
            ])

        if client_data.get('email'):
            client_info_rows.insert(3, [
                Paragraph("<b>Email:</b>", styleN), 
                Paragraph(str(client_data.get('email')), styleN)
            ])

        # Создаем таблицу
        client_table = Table(client_info_rows, colWidths=[40*mm, 140*mm])
        story.append(client_table)
        story.append(Spacer(1, 15))

        # --- Варианты кондиционеров ---
        for variant in aircon_variants:
            # Заголовок варианта
            if variant.get('title'):
                story.append(Paragraph(variant['title'], styleVariantTitle))
            
            # Описание варианта с графическими значками
            if variant.get('description'):
                # Заменяем маркеры на графические символы
                desc = variant['description'].replace('●', '•').replace('–', '•')
                story.append(Paragraph(desc, styleVariantDesc))
            
            # Таблица кондиционеров для варианта
            if variant.get('items'):
                # Заголовки таблицы
                ac_table_data = [[
                    Paragraph("Наименование товара", styleTableHeader),
                    Paragraph("Характеристики", styleTableHeader),
                    Paragraph("Ед. изм.", styleTableHeader),
                    Paragraph("Кол-во", styleTableHeader),
                    Paragraph("Цена за ед., BYN", styleTableHeader),
                    Paragraph("Скидка, %", styleTableHeader),
                    Paragraph("Сумма с учетом скидки, BYN", styleTableHeader),
                    Paragraph("Срок поставки", styleTableHeader)
                ]]
                
                for ac in variant['items']:
                    price = float(ac.get('price', 0))
                    qty = int(ac.get('qty', 1))
                    discount = float(ac.get('discount_percent', 0))
                    total_with_discount = price * qty * (1 - discount / 100)
                    
                    # Формируем характеристики и описание
                    specs_text = ""
                    if ac.get('specifications'):
                        specs_text = ", ".join([str(s) for s in ac['specifications']])
                    if ac.get('short_description'):
                        specs_text += f"\n{ac['short_description']}"
                    
                    ac_table_data.append([
                        Paragraph(ac.get('name', ''), styleTableCell),
                        Paragraph(specs_text, styleTableCell),
                        Paragraph(ac.get('unit', 'шт.'), styleTableCell),
                        Paragraph(str(qty), styleTableCell),
                        Paragraph(f"{price:.2f}", styleTableCell),
                        Paragraph(f"{discount:.2f}", styleTableCell),
                        Paragraph(f"{total_with_discount:.2f}", styleTableCell),
                        Paragraph(ac.get('delivery', 'в наличии'), styleTableCell)
                    ])
                
                ac_table = Table(
                    ac_table_data, 
                    colWidths=[45*mm, 50*mm, 15*mm, 15*mm, 20*mm, 15*mm, 25*mm, 20*mm]
                )
                ac_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('ALIGN', (4,1), (6,-1), 'RIGHT'),
                    ('ALIGN', (3,0), (3,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('WRAP', (1,1), (1,-1), True),  # Перенос текста в колонке характеристик
                ]))
                story.append(ac_table)
                story.append(Spacer(1, 15))

        # --- Таблица комплектующих ---
        total_components = 0
        if components:
            story.append(Paragraph("<b>Комплектующие и материалы:</b>", styleBold))
            story.append(Spacer(1, 8))
            comp_table_data = [[
                Paragraph("Наименование", styleTableHeader),
                Paragraph("Ед. изм.", styleTableHeader),
                Paragraph("Кол-во", styleTableHeader),
                Paragraph("Цена за ед., BYN", styleTableHeader),
                Paragraph("Скидка, %", styleTableHeader),
                Paragraph("Сумма с учетом скидки, BYN", styleTableHeader)
            ]]
            
            for comp in components:
                price = float(comp.get('price', 0))
                unit = comp.get('unit', 'шт.')
                if unit == 'м.':
                    qty_or_length = float(comp.get('length', 0.0))
                else:
                    qty_or_length = int(comp.get('qty', 0))
                discount = float(comp.get('discount_percent', 0))
                total_with_discount = price * qty_or_length * (1 - discount / 100)
                total_components += total_with_discount
                
                comp_table_data.append([
                    Paragraph(comp.get('name', ''), styleTableCell),
                    Paragraph(unit, styleTableCell),
                    Paragraph(str(qty_or_length), styleTableCell),
                    Paragraph(f"{price:.2f}", styleTableCell),
                    Paragraph(f"{discount:.2f}", styleTableCell),
                    Paragraph(f"{total_with_discount:.2f}", styleTableCell)
                ])
            
            # Итоговая строка для комплектующих
            comp_table_data.append([
                Paragraph("Итого", styleTableHeader),
                '', '', '', '',
                Paragraph(f"{total_components:.2f}", styleTableHeader)
            ])
            
            comp_table = Table(
                comp_table_data, 
                colWidths=[60*mm, 20*mm, 15*mm, 25*mm, 15*mm, 25*mm]
            )
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ALIGN', (3,1), (5,-1), 'RIGHT'),
                ('ALIGN', (2,0), (2,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('SPAN', (0,-1), (4,-1)),
                ('BACKGROUND', (0,-1), (-1,-1), colors.white),
                ('FONTNAME', (0,-1), (-1,-1), 'Arial-Bold'),
            ]))
            story.append(comp_table)
            story.append(Spacer(1, 15))

        # --- Блок работ ---
        # Явно приводим installation_price к числу и логируем
        installation_price = 0.0
        try:
            installation_price = float(order_params.get('installation_price', 0) or 0)
        except Exception as e:
            logger.error(f"Ошибка преобразования installation_price: {e}")
            installation_price = 0.0
        logger.info(f"Стоимость работ (installation_price): {installation_price}")
        # Всегда отображаем блок работ
        work_table_data = [
            [Paragraph("Монтажные работы", styleTableCell), Paragraph(f"{installation_price:.2f}", styleTableCell)]
        ]
        work_table = Table(
            work_table_data, 
            colWidths=[140*mm, 30*mm]
        )
        work_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        story.append(work_table)
        story.append(Spacer(1, 15))

        # --- Расчет итоговой суммы ---
        # Суммируем только комплектующие и работы, кондиционеры не суммируются
        total_pay = total_components + installation_price
        
        # --- Итоговая сумма ---
        styleTotalNote = ParagraphStyle('TotalNote', parent=styleBold, fontSize=9, spaceAfter=0, spaceBefore=0)
        total_table = Table([
            [
                Paragraph(f"<b>ИТОГО К ОПЛАТЕ:</b>", styleBold),
                Paragraph(f"<b>{total_pay:.2f} BYN</b>", styleBold),
                Paragraph(f"<b>+ стоимость выбранного кондиционера</b>", styleTotalNote)
            ]
        ], colWidths=[80*mm, 50*mm, 70*mm])
        total_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(total_table)
        story.append(Spacer(1, 20))

        # --- Условия и примечания ---
        story.append(Paragraph("<b>Условия поставки и монтажа:</b>", styleBold))
        story.append(Paragraph("• Монтаж осуществляется в течение 3-5 рабочих дней после оплаты", styleSmall))
        story.append(Paragraph("• Гарантия на оборудование - 3 года, на монтажные работы - 2 года", styleSmall))
        story.append(Paragraph("• Цены указаны без учета НДС", styleSmall))
        story.append(Spacer(1, 10))

        # --- Сохранение PDF ---
        try:
            doc.build(story)
            logger.info(f"PDF-файл '{file_path}' успешно сгенерирован.")
            return file_path
        except Exception as e:
            logger.error(f"Ошибка при генерации PDF: {e}", exc_info=True)
            raise
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}", exc_info=True)
        raise

# --- Асинхронная обёртка для генерации PDF ---
async def generate_commercial_offer_pdf_async(*args, **kwargs):
    """
    Асинхронная обёртка для generate_commercial_offer_pdf.
    Вызывает sync-функцию в отдельном потоке через asyncio.to_thread,
    чтобы не блокировать event loop.
    Используйте только для вызова из async-кода (например, FastAPI backend).
    """
    return await asyncio.to_thread(generate_commercial_offer_pdf, *args, **kwargs)