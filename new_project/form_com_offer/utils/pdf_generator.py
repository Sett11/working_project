import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from db import models
from utils.mylogger import Logger

logger = Logger("pdf_generator", "logs/pdf_generator.log")

def create_kp_pdf(order: models.Order, aircons: list[models.AirConditioner], components: list[models.Component]) -> str:
    """
    Создает PDF-файл коммерческого предложения.
    """
    # Уникальное имя файла
    file_name = f"user_data/KP_{order.client.full_name.replace(' ', '_')}_{datetime.date.today()}.pdf"
    
    doc = SimpleDocTemplate(file_name, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    logger.info(f"Начало генерации PDF для заказа ID: {order.id}")

    # 1. Шапка документа
    # TODO: Добавить логотип
    story.append(Paragraph("ООО 'Эвериз Сервис'", styles['h1']))
    story.append(Paragraph("г. Минск, ул. Орловс��ая, 40, пом. 256, 220030", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # 2. Информация о предложении
    story.append(Paragraph(f"КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ № {order.id} от {datetime.date.today()}", styles['h2']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"Заказчик: {order.client.full_name}, {order.client.phone}", styles['Normal']))
    story.append(Paragraph(f"Адрес объекта: {order.client.address}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # 3. Таблица с товарами
    data = [['Наименование', 'Бренд', 'Цена (BYN)', 'Кол-во', 'Сумма (BYN)']]
    
    # Добавляем кондиционеры
    for ac in aircons:
        price = ac.retail_price_byn or 0
        quantity = 1 # Пока условно 1
        total = price * quantity
        data.append([ac.model_name, ac.brand, f"{price:.2f}", str(quantity), f"{total:.2f}"])
        
    # Добавляем комплектующие
    for comp in components:
        price = comp.price or 0
        quantity = 1 # TODO: Рассчитывать количество
        total = price * quantity
        data.append([comp.name, comp.manufacturer or '', f"{price:.2f}", str(quantity), f"{total:.2f}"])

    # Стиль таблицы
    table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ])
    
    tbl = Table(data)
    tbl.setStyle(table_style)
    story.append(tbl)
    story.append(Spacer(1, 0.2*inch))

    # 4. Итоговая сумма
    # TODO: Реализовать расчет итоговой суммы с учетом скидки
    # total_sum = ...
    # story.append(Paragraph(f"Итого к оплате: {total_sum:.2f} BYN", styles['h3']))

    try:
        doc.build(story)
        logger.info(f"PDF-файл '{file_name}' успешно сгенерирован.")
        return file_name
    except Exception as e:
        logger.error(f"Ошибка при сборке PDF-документа: {e}", exc_info=True)
        return ""
