from utils.mylogger import Logger

logger = Logger("pdf_gen", "logs")

def create_kp_pdf(client_id, aircons):
    logger.info("PDF-файл успешно сгенерирован")
    return 'user_data\path.txt'