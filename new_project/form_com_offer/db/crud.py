from sqlalchemy.orm import Session
from . import models, schemas
from utils.mylogger import Logger
# TODO: Добавить функцию для хеширования пароля
# from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = Logger(name=__name__, log_file="db.log")

# --- User CRUD ---

def get_user_by_username(db: Session, username: str):
    """Получение пользователя по имени."""
    logger.debug(f"Запрос на получение пользователя по имени: {username}")
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Создание нового пользователя."""
    logger.info(f"Создание нового пользователя: {user.username}")
    # hashed_password = pwd_context.hash(user.password) # Раскомментировать, когда будет безопасность
    hashed_password = user.password + "_hashed" # Временная заглушка
    db_user = models.User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Пользователь '{user.username}' успешно создан с id={db_user.id}.")
    return db_user

# --- Client CRUD ---

def get_client_by_phone(db: Session, phone: str):
    """Получение клиента по номеру телефона."""
    logger.debug(f"Запрос на получение клиента по номеру телефона: {phone}")
    return db.query(models.Client).filter(models.Client.phone == phone).first()

def create_client(db: Session, client: schemas.ClientCreate) -> models.Client:
    """Создание нового клиента."""
    logger.info(f"Создание нового клиента: {client.full_name}")
    db_client = models.Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    logger.info(f"Клиент '{client.full_name}' успешно создан с id={db_client.id}.")
    return db_client

# --- Product CRUD ---

def get_air_conditioners(db: Session, skip: int = 0, limit: int = 100):
    """Получение списка кондиционеров с пагинацией."""
    logger.debug(f"Запрос на получение списка кондиционеров (skip={skip}, limit={limit})")
    return db.query(models.AirConditioner).offset(skip).limit(limit).all()

def get_components(db: Session, skip: int = 0, limit: int = 100):
    """Получение списка комплектующих с пагинацией."""
    logger.debug(f"Запрос на получение списка комплектующих (skip={skip}, limit={limit})")
    return db.query(models.Component).offset(skip).limit(limit).all()

# --- Order CRUD ---

def create_order(db: Session, order: schemas.OrderCreate) -> models.Order:
    """Создание нового заказа."""
    logger.info(f"Создание нового заказа для клиента с id={order.client_id}")
    db_order = models.Order(**order.model_dump())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    logger.info(f"Заказ для клиента с id={order.client_id} успешно создан с id={db_order.id}.")
    return db_order
