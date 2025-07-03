from utils.mylogger import Logger

logger = Logger("crud", "logs")

def save_client_data(name, phone, mail, address, date, area, type_room, discount):
    logger.info("Данные клиента успешно сохранены")
    return