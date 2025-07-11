"""
Модуль для выполнения CRUD-операций (Create, Read, Update, Delete) с базой данных.

Здесь определены функции для взаимодействия с моделями SQLAlchemy:
- User (пользователь)
- Client (клиент)
- AirConditioner (кондиционер)
- Component (комплектующее)
- Order (заказ)

Каждая функция принимает сессию БД и необходимые данные, выполняет операцию
и возвращает результат. Ведётся подробное логирование всех действий.
"""
from sqlalchemy.orm import Session
from . import models, schemas
from utils.mylogger import Logger
# TODO: Добавить и настроить безопасное хеширование паролей.
# from passlib.context import CryptContext

# Инициализация контекста для хеширования паролей (пока отключено).
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Инициализация логгера для операций с базой данных.
# log_file указывается без папки logs, чтобы использовать дефолтную директорию логов.
logger = Logger(name=__name__, log_file="db.log")


# --- CRUD-операции для Пользователей (User) ---

def get_user_by_username(db: Session, username: str) -> models.User | None:
    """
    Получение пользователя по его имени (username).

    Args:
        db (Session): Сессия базы данных.
        username (str): Имя пользователя для поиска.

    Returns:
        models.User | None: Объект пользователя или None, если пользователь не найден.
    """
    logger.debug(f"Выполняется запрос на получение пользователя по имени: {username}")
    # Выполняем запрос к таблице пользователей по username
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        logger.debug(f"Пользователь '{username}' найден с id={user.id}.")
    else:
        logger.debug(f"Пользователь с именем '{username}' не найден.")
    return user


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """
    Создание нового пользователя в базе данных.

    Args:
        db (Session): Сессия базы данных.
        user (schemas.UserCreate): Pydantic-схема с данными нового пользователя.

    Returns:
        models.User: Созданный объект пользователя.
    """
    logger.info(f"Начало создания нового пользователя: {user.username}")
    # Временная заглушка для пароля. Необходимо заменить на реальное хеширование.
    # hashed_password = pwd_context.hash(user.password)
    hashed_password = user.password + "_hashed"
    
    db_user = models.User(username=user.username, hashed_password=hashed_password, role=user.role)
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Пользователь '{user.username}' успешно создан с id={db_user.id}.")
        return db_user
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя '{user.username}': {e}", exc_info=True)
        db.rollback()
        raise


# --- CRUD-операции для Клиентов (Client) ---

def get_client_by_phone(db: Session, phone: str) -> models.Client | None:
    """
    Получение клиента по его номеру телефона.

    Args:
        db (Session): Сессия базы данных.
        phone (str): Номер телефона для поиска.

    Returns:
        models.Client | None: Объект клиента или None, если клиент не найден.
    """
    logger.debug(f"Выполняется запрос на получение клиента по номеру телефона: {phone}")
    # Выполняем запрос к таблице клиентов по номеру телефона
    client = db.query(models.Client).filter(models.Client.phone == phone).first()
    if client:
        logger.debug(f"Клиент с телефоном '{phone}' найден: {client.full_name} (id={client.id}).")
    else:
        logger.debug(f"Клиент с телефоном '{phone}' не найден.")
    return client


def create_client(db: Session, client: schemas.ClientCreate) -> models.Client:
    """
    Создание нового клиента в базе данных.

    Args:
        db (Session): Сессия базы данных.
        client (schemas.ClientCreate): Pydantic-схема с данными нового клиента.

    Returns:
        models.Client: Созданный объект клиента.
    """
    logger.info(f"Начало создания нового клиента: {client.full_name}")
    db_client = models.Client(**client.model_dump())
    
    try:
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        logger.info(f"Клиент '{client.full_name}' успешно создан с id={db_client.id}.")
        return db_client
    except Exception as e:
        logger.error(f"Ошибка при создании клиента '{client.full_name}': {e}", exc_info=True)
        db.rollback()
        raise


# --- CRUD-операции для Продуктов (Product) ---

def get_air_conditioners(db: Session, skip: int = 0, limit: int = 100) -> list[models.AirConditioner]:
    """
    Получение списка кондиционеров с пагинацией.

    Args:
        db (Session): Сессия базы данных.
        skip (int): Количество записей для пропуска.
        limit (int): Максимальное количество записей для возврата.

    Returns:
        list[models.AirConditioner]: Список объектов кондиционеров.
    """
    logger.debug(f"Запрос на получение списка кондиционеров (skip={skip}, limit={limit})")
    # Получаем кондиционеры с пагинацией
    return db.query(models.AirConditioner).offset(skip).limit(limit).all()


def get_components(db: Session, skip: int = 0, limit: int = 100) -> list[models.Component]:
    """
    Получение списка комплектующих с пагинацией.

    Args:
        db (Session): Сессия базы данных.
        skip (int): Количество записей для пропуска.
        limit (int): Максимальное количество записей для возврата.

    Returns:
        list[models.Component]: Список объектов комплектующих.
    """
    logger.debug(f"Запрос на получение списка комплектующих (skip={skip}, limit={limit})")
    # Получаем комплектующие с пагинацией
    return db.query(models.Component).offset(skip).limit(limit).all()


def get_components_by_filters(db: Session, filters: dict) -> list[models.Component]:
    """
    Получение списка комплектующих по заданным фильтрам.

    Args:
        db (Session): Сессия базы данных.
        filters (dict): Словарь с фильтрами (например, 'category', 'price_limit').

    Returns:
        list[models.Component]: Отфильтрованный список комплектующих.
    """
    logger.debug(f"Запрос на получение комплектующих с фильтрами: {filters}")
    
    query = db.query(models.Component)
    
    # Применяем фильтры, если они указаны.
    if filters.get("category"):
        query = query.filter(models.Component.category == filters["category"])
    
    if filters.get("price_limit"):
        query = query.filter(models.Component.price <= filters["price_limit"])
    
    # Фильтруем только товары, которые есть в наличии.
    query = query.filter(models.Component.in_stock == True)
    
    # Сортируем результат по цене (от дешёвых к дорогим).
    query = query.order_by(models.Component.price.asc())
    
    components = query.all()
    logger.info(f"Найдено {len(components)} комплектующих по фильтрам: {filters}")
    return components


def get_all_components(db: Session) -> list[models.Component]:
    """
    Получение полного списка всех комплектующих, имеющихся в наличии.

    Args:
        db (Session): Сессия базы данных.

    Returns:
        list[models.Component]: Список всех комплектующих в наличии.
    """
    logger.debug("Запрос на получение всех комплектующих в наличии.")
    
    query = db.query(models.Component)
    
    # Фильтруем только товары в наличии.
    query = query.filter(models.Component.in_stock == True)
    
    # Сортируем по категории, а затем по цене.
    query = query.order_by(models.Component.category.asc(), models.Component.price.asc())
    
    components = query.all()
    logger.info(f"Всего получено {len(components)} комплектующих из БД.")
    return components


# --- CRUD-операции для Заказов (Order) ---

def create_order(db: Session, order: schemas.OrderCreate) -> models.Order:
    """
    Создание нового заказа в базе данных.

    Args:
        db (Session): Сессия базы данных.
        order (schemas.OrderCreate): Pydantic-схема с данными нового заказа.

    Returns:
        models.Order: Созданный объект заказа.
    """
    logger.info(f"Начало создания нового заказа для клиента с id={order.client_id}")
    db_order = models.Order(**order.model_dump())
    
    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        logger.info(f"Заказ для клиента id={order.client_id} успешно создан с id={db_order.id}.")
        return db_order
    except Exception as e:
        logger.error(f"Ошибка при создании заказа для клиента id={order.client_id}: {e}", exc_info=True)
        db.rollback()
        raise
