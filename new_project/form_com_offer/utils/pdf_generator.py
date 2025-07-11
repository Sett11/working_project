"""
Модуль генерации PDF-файлов коммерческих предложений.

Использует библиотеку reportlab для создания PDF-документов с таблицами товаров и комплектующих.
"""
import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from utils.mylogger import Logger

logger = Logger("pdf_generator", "pdf_generator.log")


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
        client_data (dict): Данные клиента (full_name, phone, address, email).
        order_params (dict): Параметры заказа (дата, площадь, тип помещения и др.).
        aircons (list): Список кондиционеров (dict: name, description, price, qty).
        components (list): Список комплектующих (dict: name, price, qty).
        discount_percent (float): Скидка в процентах (0-100).
        offer_number (str): Номер КП (если None — генерируется автоматически).
        save_dir (str): Папка для сохранения PDF (относительно корня проекта).

    Returns:
        str: Абсолютный путь к сгенерированному PDF-файлу.
    """
    # Создаём директорию для сохранения, если не существует
    abs_save_dir = os.path.abspath(save_dir)
    os.makedirs(abs_save_dir, exist_ok=True)

    # Формируем имя файла
    today = datetime.date.today().strftime("%d-%m-%Y")
    offer_number = offer_number or f"{today}_{client_data.get('full_name','').replace(' ', '_')}"
    file_name = f"КП_{offer_number}.pdf"
    file_path = os.path.join(abs_save_dir, file_name)

    # Стили
    styles = getSampleStyleSheet()
    styleH = styles['Heading1']
    styleN = styles['Normal']
    styleTableHeader = ParagraphStyle('TableHeader', parent=styles['Normal'], alignment=1, fontSize=10, fontName='Helvetica-Bold')
    styleTableCell = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=10)

    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    story = []

    # --- Шапка ---
    story.append(Paragraph("<b>КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ</b>", styleH))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Номер КП:</b> {offer_number}", styleN))
    story.append(Paragraph(f"<b>Дата:</b> {today}", styleN))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>ООО 'Эвериз Сервис'</b>", styleN))
    story.append(Paragraph("г. Минск, ул. Орловская, 40, пом. 256, 220030", styleN))
    story.append(Spacer(1, 12))

    # --- Данные клиента ---
    story.append(Paragraph(f"<b>Клиент:</b> {client_data.get('full_name','')}", styleN))
    story.append(Paragraph(f"<b>Телефон:</b> {client_data.get('phone','')}", styleN))
    if client_data.get('email'):
        story.append(Paragraph(f"<b>Email:</b> {client_data.get('email')}", styleN))
    if client_data.get('address'):
        story.append(Paragraph(f"<b>Адрес объекта:</b> {client_data.get('address')}", styleN))
    story.append(Spacer(1, 12))

    # --- Параметры заказа ---
    if order_params:
        params_str = ", ".join([f"{k}: {v}" for k, v in order_params.items() if v])
        story.append(Paragraph(f"<b>Параметры заказа:</b> {params_str}", styleN))
        story.append(Spacer(1, 12))

    # --- Таблица кондиционеров ---
    if aircons:
        story.append(Paragraph("<b>Подобранные кондиционеры:</b>", styleN))
        ac_table_data = [[
            Paragraph("Наименование", styleTableHeader),
            Paragraph("Описание", styleTableHeader),
            Paragraph("Цена за шт., BYN", styleTableHeader),
            Paragraph("Кол-во", styleTableHeader),
            Paragraph("Сумма, BYN", styleTableHeader)
        ]]
        ac_total = 0
    for ac in aircons:
            price = float(ac.get('price', 0))
            qty = int(ac.get('qty', 1))
            price_with_discount = round(price * (1 - discount_percent/100), 2)
            total = round(price_with_discount * qty, 2)
            ac_total += total
            ac_table_data.append([
                Paragraph(str(ac.get('name','')), styleTableCell),
                Paragraph(str(ac.get('description','')), styleTableCell),
                Paragraph(f"{price_with_discount:.2f}", styleTableCell),
                Paragraph(str(qty), styleTableCell),
                Paragraph(f"{total:.2f}", styleTableCell)
            ])
            ac_table = Table(ac_table_data, colWidths=[60*mm, 60*mm, 30*mm, 20*mm, 30*mm])
            ac_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(ac_table)
            story.append(Spacer(1, 12))
    else:
        ac_total = 0

    # --- Таблица комплектующих ---
    if components:
        story.append(Paragraph("<b>Комплектующие:</b>", styleN))
        comp_table_data = [[
            Paragraph("Наименование", styleTableHeader),
            Paragraph("Кол-во", styleTableHeader),
            Paragraph("Цена за шт., BYN", styleTableHeader),
            Paragraph("Сумма, BYN", styleTableHeader)
        ]]
        comp_total = 0
    for comp in components:
            price = float(comp.get('price', 0))
            qty = int(comp.get('qty', 1))
            price_with_discount = round(price * (1 - discount_percent/100), 2)
            total = round(price_with_discount * qty, 2)
            comp_total += total
            comp_table_data.append([
                Paragraph(str(comp.get('name','')), styleTableCell),
                Paragraph(str(qty), styleTableCell),
                Paragraph(f"{price_with_discount:.2f}", styleTableCell),
                Paragraph(f"{total:.2f}", styleTableCell)
            ])
            comp_table = Table(comp_table_data, colWidths=[80*mm, 30*mm, 30*mm, 30*mm])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(comp_table)
            story.append(Spacer(1, 12))
    else:
        comp_total = 0

    # --- Итоги ---
    total_sum = ac_total + comp_total
    discount_sum = round(total_sum * discount_percent/100, 2)
    to_pay = round(total_sum, 2)
    story.append(Paragraph(f"<b>Сумма без скидки:</b> {total_sum + discount_sum:.2f} BYN", styleN))
    story.append(Paragraph(f"<b>Скидка:</b> {discount_sum:.2f} BYN", styleN))
    story.append(Paragraph(f"<b>Итого к оплате:</b> {to_pay:.2f} BYN", styleN))
    story.append(Spacer(1, 12))

    # --- Сохранение PDF ---
    try:
        doc.build(story)
        logger.info(f"PDF-файл '{file_path}' успешно сгенерирован.")
        return file_path
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}", exc_info=True)
        return ""
