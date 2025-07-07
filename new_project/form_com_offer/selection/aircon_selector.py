from utils.mylogger import Logger

logger = Logger("aircons_select", "logs")

def get_filtered_aircons(area, type_room, wifi, inverter, x1, x2, x3, brand):
    """Заглушка для теста интерфейса. Позже заменим на реальную функцию."""
    logger.info("Кондиционеры успешно подобраны")
    return [
        {"model": "Mitsubishi MSZ-LN25", "price": 899, "wifi": True, "inverter": True},
        {"model": "Ballu BSEI-12HN1", "price": 499, "wifi": False, "inverter": False},
    ]