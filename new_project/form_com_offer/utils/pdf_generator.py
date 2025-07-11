"""
Модуль генерации PDF-файлов коммерческих предложений.
Использует библиотеку reportlab для создания PDF-документов.
"""
import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from utils.mylogger import Logger
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

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
    aircons: list,
    components: list,
    discount_percent: float,
    offer_number: str = None,
    save_dir: str = "commercial_offer_pdf"
) -> str:
    """
    Генерирует PDF-файл коммерческого предложения по заданным данным.
    
    Args:
        client_data (dict): Данные клиента (full_name, phone, address, email)
        order_params (dict): Параметры заказа (room_type, installation_price)
        aircons (list): Список кондиционеров (dict: name, manufacturer, price, qty, unit, delivery)
        components (list): Список комплектующих (dict: name, price, qty, unit)
        discount_percent (float): Скидка в процентах (0-100)
        offer_number (str): Номер КП (если None - генерируется автоматически)
        save_dir (str): Папка для сохранения PDF
        
    Returns:
        str: Абсолютный путь к сгенерированному PDF-файлу
    """
    # Создаем директорию для сохранения
    abs_save_dir = os.path.abspath(save_dir)
    os.makedirs(abs_save_dir, exist_ok=True)

    # Формируем имя файла
    today = datetime.date.today().strftime("%d-%m-%Y")
    offer_number = offer_number or f"{today}_{client_data.get('full_name','').replace(' ', '_')}"
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
    story.append(Paragraph("г. Минск, ул. Орловская, 40, пом. 25б, 220030", styleN))
    story.append(Paragraph("УНП 192812488", styleN))
    story.append(Paragraph("BY29 MTBK 3012 0001 0933 0013 0402", styleN))
    story.append(Paragraph("в ЗАО «МТБанк», БИК MTBKBY22", styleN))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ</b>", styleH))
    story.append(Spacer(1, 6))
    
    # Номер и дата КП
    story.append(Table([
        [Paragraph("<b>Номер КП:</b>", styleN), Paragraph(offer_number, styleN)],
        [Paragraph("<b>Дата:</b>", styleN), Paragraph(today, styleN)]
    ], colWidths=[30*mm, 100*mm]))
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
            Paragraph(value, styleN)
        ])

    if client_data.get('email'):
        client_info_rows.insert(3, [
            Paragraph("<b>Email:</b>", styleN), 
            Paragraph(client_data.get('email'), styleN)
        ])

    # Создаем таблицу
    client_table = Table(client_info_rows, colWidths=[40*mm, 140*mm])
    story.append(client_table)
    story.append(Spacer(1, 15))

    # --- Таблица кондиционеров ---
    ac_total = 0
    if aircons:
        story.append(Paragraph("<b>Подобранные кондиционеры:</b>", styleBold))
        # Заголовки таблицы
        ac_table_data = [[
            Paragraph("Наименование товара", styleTableHeader),
            Paragraph("Производитель", styleTableHeader),
            Paragraph("Ед. изм.", styleTableHeader),
            Paragraph("Кол-во", styleTableHeader),
            Paragraph("Цена за ед., BYN", styleTableHeader),
            Paragraph("Сумма, BYN", styleTableHeader),
            Paragraph("Срок поставки", styleTableHeader)
        ]]
        
        for ac in aircons:
            price = float(ac.get('price', 0))
            qty = int(ac.get('qty', 1))
            total = price * qty
            ac_total += total
            
            ac_table_data.append([
                Paragraph(ac.get('name', ''), styleTableCell),
                Paragraph(ac.get('manufacturer', ''), styleTableCell),
                Paragraph(ac.get('unit', 'шт.'), styleTableCell),
                Paragraph(str(qty), styleTableCell),
                Paragraph(f"{price:.2f}", styleTableCell),
                Paragraph(f"{total:.2f}", styleTableCell),
                Paragraph(ac.get('delivery', 'в наличии'), styleTableCell)
            ])
        
        # Итоговая строка (без скидки)
        ac_table_data.append([
            Paragraph("Итого", styleTableHeader),
            '', '', '', '',
            Paragraph(f"{ac_total:.2f}", styleTableHeader),
            ''
        ])
        
        ac_table = Table(
            ac_table_data, 
            colWidths=[60*mm, 30*mm, 20*mm, 15*mm, 25*mm, 25*mm, 25*mm]
        )
        ac_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (3,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('SPAN', (0,-1), (4,-1)),  # Объединение ячеек для "Итого"
            ('BACKGROUND', (0,-1), (-1,-1), colors.white),
            ('FONTNAME', (0,-1), (-1,-1), 'Arial-Bold'),
        ]))
        story.append(ac_table)
        story.append(Spacer(1, 15))

    # --- Таблица комплектующих ---
    comp_total = 0
    if components:
        story.append(Paragraph("<b>Комплектующие и материалы:</b>", styleBold))
        comp_table_data = [[
            Paragraph("Наименование", styleTableHeader),
            Paragraph("Ед. изм.", styleTableHeader),
            Paragraph("Кол-во", styleTableHeader),
            Paragraph("Цена за ед., BYN", styleTableHeader),
            Paragraph("Сумма, BYN", styleTableHeader)
        ]]
        
        for comp in components:
            price = float(comp.get('price', 0))
            qty = int(comp.get('qty', 1))
            total = price * qty
            comp_total += total
            
            comp_table_data.append([
                Paragraph(comp.get('name', ''), styleTableCell),
                Paragraph(comp.get('unit', 'шт.'), styleTableCell),
                Paragraph(str(qty), styleTableCell),
                Paragraph(f"{price:.2f}", styleTableCell),
                Paragraph(f"{total:.2f}", styleTableCell)
            ])
        
        # Итоговая строка (без скидки)
        comp_table_data.append([
            Paragraph("Итого", styleTableHeader),
            '', '',
            Paragraph(f"{comp_total:.2f}", styleTableHeader),
            ''
        ])
        
        comp_table = Table(
            comp_table_data, 
            colWidths=[80*mm, 25*mm, 20*mm, 30*mm, 25*mm]
        )
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (2,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('SPAN', (0,-1), (2,-1)),  # Объединение ячеек для "Итого"
            ('BACKGROUND', (0,-1), (-1,-1), colors.white),
            ('FONTNAME', (0,-1), (-1,-1), 'Arial-Bold'),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 15))

    # --- Блок работ ---
    installation_price = 0
    if order_params.get('installation_price', 0) > 0:
        installation_price = float(order_params['installation_price'])
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

    # --- Расчет итоговой суммы со скидкой ---
    total_without_discount = ac_total + comp_total + installation_price
    discount_value = total_without_discount * discount_percent / 100
    total_with_discount = total_without_discount - discount_value
    
    # --- Итоговая сумма ---
    total_table = Table([
        [Paragraph(f"<b>Общая сумма:</b>", styleBold), Paragraph(f"{total_without_discount:.2f} BYN", styleN)],
        [Paragraph(f"<b>Скидка {discount_percent}%:</b>", styleBold), Paragraph(f"-{discount_value:.2f} BYN", styleN)],
        [Paragraph(f"<b>ИТОГО К ОПЛАТЕ:</b>", styleBold), Paragraph(f"{total_with_discount:.2f} BYN", styleBold)]
    ], colWidths=[100*mm, 50*mm])
    
    story.append(total_table)
    story.append(Spacer(1, 20))

    # --- Условия и примечания ---
    story.append(Paragraph("<b>Условия поставки и монтажа:</b>", styleBold))
    story.append(Paragraph("• Монтаж осуществляется в течение 3-5 рабочих дней после оплаты", styleSmall))
    story.append(Paragraph("• Гарантия на оборудование - 3 года, на монтажные работы - 2 года", styleSmall))
    story.append(Paragraph("• Цены указаны без учета НДС", styleSmall))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Менеджер: </b>Бурак Д.С. +375 44 55 123 44", styleSmall))

    # --- Сохранение PDF ---
    try:
        doc.build(story)
        logger.info(f"PDF-файл '{file_path}' успешно сгенерирован.")
        return file_path
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}", exc_info=True)
        return ""