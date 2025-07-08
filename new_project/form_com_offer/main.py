import uvicorn
from back.back import app
from utils.mylogger import Logger
from db import models
from db.database import engine

# Создаем все таблицы в базе данных
models.Base.metadata.create_all(bind=engine)

logger = Logger("main", "logs/main.log")

if __name__ == "__main__":
    logger.info("Запуск FastAPI-сервера")
    uvicorn.run(app, host="0.0.0.0", port=8000)
