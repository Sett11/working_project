from sqlalchemy.orm import Session
from . import models, schemas
from utils.mylogger import Logger
# TODO: Добавить функцию для хеширования пароля
# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = Logger("crud", "logs/crud.log")

# --- User CRUD ---

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    # hashed_password = pwd_context.hash(user.password) # Раскомментировать, когда будет безопасность
    hashed_password = user.password + "_hashed" # Временная заглушка
    db_user = models.User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Создан пользователь: {user.username}")
    return db_user

# --- Client CRUD ---

def get_client_by_phone(db: Session, phone: str):
    return db.query(models.Client).filter(models.Client.phone == phone).first()

def create_client(db: Session, client: schemas.ClientCreate) -> models.Client:
    db_client = models.Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    logger.info(f"Создан клиент: {client.full_name}")
    return db_client

# --- Product CRUD ---

def get_air_conditioners(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AirConditioner).offset(skip).limit(limit).all()

def get_components(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Component).offset(skip).limit(limit).all()

# --- Order CRUD ---

def create_order(db: Session, order: schemas.OrderCreate) -> models.Order:
    db_order = models.Order(**order.model_dump())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    logger.info(f"Создан заказ ID: {db_order.id} для клиента ID: {order.client_id}")
    return db_order
