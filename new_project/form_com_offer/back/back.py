from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List

from db import models, schemas
from db.database import get_db
from utils.mylogger import Logger

# Инициализация логгера
logger = Logger("back", "logs/back.log")

app = FastAPI(title="API для автоматизации продаж")

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI приложение запускается")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI приложение останавливается")


@app.get("/components/", response_model=List[schemas.Component])
def read_components(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Получает список всех комплектующих из базы данных.
    """
    logger.info(f"Запрос на получение списка комплектующих: skip={skip}, limit={limit}")
    try:
        components = db.query(models.Component).offset(skip).limit(limit).all()
        logger.info(f"Успешно получено {len(components)} комплектующих")
        return components
    except Exception as e:
        logger.error(f"Ошибка при получении комплектующих: {e}", exc_info=True)
        raise

