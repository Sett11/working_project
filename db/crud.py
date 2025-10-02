"""
Модуль для выполнения CRUD-операций (Create, Read, Update, Delete) с базой данных.

Здесь определены функции для взаимодействия с моделями SQLAlchemy:
- Client (клиент)
- AirConditioner (кондиционер)
- Component (комплектующее)
- Order (заказ)

Каждая функция принимает сессию БД и необходимые данные, выполняет операцию
и возвращает результат. Ведётся подробное логирование всех действий.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models, schemas
from utils.mylogger import Logger
from datetime import datetime
import json

logger = Logger(name=__name__, log_file="db.log")

# --- CRUD-операции для Пользователей (User) ---

async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:
    """
    Получение пользователя по логину.

    Args:
        db (AsyncSession): Сессия базы данных.
        username (str): Логин пользователя.

    Returns:
        models.User | None: Объект пользователя или None, если пользователь не найден.
    """
    logger.info(f"[CRUD] get_user_by_username: username={username}")
    result = await db.execute(select(models.User).where(models.User.username == username))
    user = result.scalar_one_or_none()
    logger.info(f"[CRUD] get_user_by_username: found={bool(user)}")
    return user


async def create_user(db: AsyncSession, user: schemas.UserCreate, password_hash: str) -> models.User:
    """
    Создание нового пользователя в базе данных.

    Args:
        db (AsyncSession): Сессия базы данных.
        user (schemas.UserCreate): Pydantic-схема с данными нового пользователя.
        password_hash (str): Хешированный пароль.

    Returns:
        models.User: Созданный объект пользователя.
    """
    logger.info(f"[CRUD] create_user: username={user.username}")
    db_user = models.User(
        username=user.username,
        password_hash=password_hash
    )
    
    try:
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        logger.info(f"Пользователь '{user.username}' успешно создан с id={db_user.id}.")
        return db_user
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя '{user.username}': {e}", exc_info=True)
        await db.rollback()
        raise


async def update_user_token(db: AsyncSession, user_id: int, token: str, expires_at: datetime) -> bool:
    """
    Обновление токена пользователя.

    Args:
        db (AsyncSession): Сессия базы данных.
        user_id (int): ID пользователя.
        token (str): Новый токен.
        expires_at (datetime): Время истечения токена.

    Returns:
        bool: True если обновление прошло успешно.
    """
    logger.info(f"[CRUD] update_user_token: user_id={user_id}")
    try:
        result = await db.execute(
            select(models.User).where(models.User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.current_token = token
            user.token_expires_at = expires_at
            user.last_login = datetime.now()
            await db.commit()
            logger.info(f"Токен пользователя {user_id} обновлен.")
            return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении токена пользователя {user_id}: {e}", exc_info=True)
        await db.rollback()
        raise


async def get_user_by_token(db: AsyncSession, token: str) -> models.User | None:
    """
    Получение пользователя по токену.

    Args:
        db (AsyncSession): Сессия базы данных.
        token (str): Токен пользователя.

    Returns:
        models.User | None: Объект пользователя или None, если токен недействителен.
    """
    logger.info(f"[CRUD] get_user_by_token: token={token[:10]}...")
    result = await db.execute(
        select(models.User).where(
            models.User.current_token == token,
            models.User.token_expires_at > datetime.now(),
            models.User.is_active == True
        )
    )
    user = result.scalar_one_or_none()
    logger.info(f"[CRUD] get_user_by_token: found={bool(user)}")
    return user


# --- CRUD-операции для Клиентов (Client) ---

async def get_client_by_phone(db: AsyncSession, phone: str) -> models.Client | None:
    """
    Получение клиента по его номеру телефона.

    Args:
        db (Session): Сессия базы данных.
        phone (str): Номер телефона для поиска.

    Returns:
        models.Client | None: Объект клиента или None, если клиент не найден.
    """
    logger.info(f"[CRUD] get_client_by_phone: phone={phone}")
    # Выполняем запрос к таблице клиентов по номеру телефона
    result = await db.execute(select(models.Client).where(models.Client.phone == phone))
    client = result.scalar_one_or_none()
    logger.info(f"[CRUD] get_client_by_phone: found={bool(client)}")
    return client


async def create_client(db: AsyncSession, client: schemas.ClientCreate) -> models.Client:
    """
    Создание нового клиента в базе данных.

    Args:
        db (Session): Сессия базы данных.
        client (schemas.ClientCreate): Pydantic-схема с данными нового клиента.

    Returns:
        models.Client: Созданный объект клиента.
    """
    logger.info(f"[CRUD] create_client: {client}")
    db_client = models.Client(**client.model_dump())
    
    try:
        db.add(db_client)
        await db.commit()
        await db.refresh(db_client)
        logger.info(f"Клиент '{client.full_name}' успешно создан с id={db_client.id}.")
        return db_client
    except Exception as e:
        logger.error(f"Ошибка при создании клиента '{client.full_name}': {e}", exc_info=True)
        await db.rollback()
        raise


async def get_or_create_client(db: AsyncSession, client_data: dict) -> models.Client:
    """
    Получение существующего клиента по телефону или создание нового.

    Args:
        db (AsyncSession): Сессия базы данных.
        client_data (dict): Данные клиента.

    Returns:
        models.Client: Объект клиента (существующий или новый).
    """
    logger.info(f"[CRUD] get_or_create_client: {client_data}")
    
    phone = client_data.get("phone")
    if not phone:
        raise ValueError("Номер телефона обязателен для поиска/создания клиента")
    
    # Сначала пытаемся найти существующего клиента по телефону
    existing_client = await get_client_by_phone(db, phone)
    if existing_client:
        logger.info(f"[CRUD] get_or_create_client: найден существующий клиент id={existing_client.id}")
        return existing_client
    
    # Если клиент не найден, создаем нового
    logger.info(f"[CRUD] get_or_create_client: создаем нового клиента")
    client_schema = schemas.ClientCreate(**client_data)
    new_client = await create_client(db, client_schema)
    return new_client


# --- CRUD-операции для Продуктов (Product) ---

async def get_air_conditioners(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[models.AirConditioner]:
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
    result = await db.execute(select(models.AirConditioner).offset(skip).limit(limit))
    return result.scalars().all()


async def get_components(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[models.Component]:
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
    result = await db.execute(select(models.Component).offset(skip).limit(limit))
    return result.scalars().all()


async def get_components_by_filters(db: AsyncSession, filters: dict) -> list[models.Component]:
    """
    Получение списка комплектующих по заданным фильтрам.

    Args:
        db (Session): Сессия базы данных.
        filters (dict): Словарь с фильтрами (например, 'category', 'price_limit').

    Returns:
        list[models.Component]: Отфильтрованный список комплектующих.
    """
    logger.debug(f"Запрос на получение комплектующих с фильтрами: {filters}")
    
    stmt = select(models.Component)
    
    # Применяем фильтры, если они указаны.
    if filters.get("category"):
        stmt = stmt.where(models.Component.category == filters["category"])
    
    if filters.get("price_limit"):
        stmt = stmt.where(models.Component.price <= filters["price_limit"])
    
    # Фильтруем только товары, которые есть в наличии.
    stmt = stmt.where(models.Component.in_stock == True)
    
    # Сортируем результат по цене (от дешёвых к дорогим).
    stmt = stmt.order_by(models.Component.price.asc())
    
    result = await db.execute(stmt)
    components = result.scalars().all()
    logger.info(f"Найдено {len(components)} комплектующих по фильтрам: {filters}")
    return components


async def get_all_components(db: AsyncSession) -> list[models.Component]:
    """
    Получение полного списка всех комплектующих, имеющихся в наличии.

    Args:
        db (Session): Сессия базы данных.

    Returns:
        list[models.Component]: Список всех комплектующих в наличии.
    """
    logger.debug("Запрос на получение всех комплектующих в наличии.")
    
    stmt = select(models.Component).where(models.Component.in_stock == True).order_by(models.Component.category.asc(), models.Component.price.asc())
    
    result = await db.execute(stmt)
    components = result.scalars().all()
    logger.info(f"Всего получено {len(components)} комплектующих из БД.")
    return components


# --- CRUD-операции для Заказов (Order) ---

async def create_order(db: AsyncSession, order: schemas.OrderCreate) -> models.Order:
    """
    Создание нового заказа в базе данных.
    """
    logger.info(f"[CRUD] create_order: {order}")
    db_order = models.Order(
        client_id=order.client_id,
        status=order.status,
        pdf_path=order.pdf_path,
        order_data=json.dumps(order.order_data, ensure_ascii=False),
        created_at=order.created_at
    )
    try:
        db.add(db_order)
        await db.commit()
        await db.refresh(db_order)
        logger.info(f"Заказ для клиента id={order.client_id} успешно создан с id={db_order.id}.")
        return db_order
    except Exception as e:
        logger.error(f"Ошибка при создании заказа для клиента id={order.client_id}: {e}", exc_info=True)
        await db.rollback()
        raise


async def update_order_by_id(db: AsyncSession, order_id: int, order_update: schemas.OrderCreate) -> models.Order | None:
    """
    Обновляет заказ по id. Если заказа нет — возвращает None.
    """
    logger.info(f"[CRUD] update_order_by_id: order_id={order_id}, order_update={order_update}")
    result = await db.execute(select(models.Order).where(models.Order.id == order_id))
    db_order = result.scalar_one_or_none()
    if not db_order:
        logger.warning(f"Заказ с id={order_id} не найден для обновления.")
        return None
    try:
        db_order.status = order_update.status
        db_order.pdf_path = order_update.pdf_path
        db_order.order_data = json.dumps(order_update.order_data, ensure_ascii=False)
        db_order.created_at = order_update.created_at
        db_order.client_id = order_update.client_id
        await db.commit()
        await db.refresh(db_order)
        logger.info(f"Заказ с id={order_id} успешно обновлён.")
        return db_order
    except Exception as e:
        logger.error(f"Ошибка при обновлении заказа id={order_id}: {e}", exc_info=True)
        await db.rollback()
        raise

# --- CRUD-операции для счетчика КП (OfferCounter) ---

async def get_or_create_offer_counter(db: AsyncSession) -> models.OfferCounter:
    """
    Получение или создание счетчика номеров КП.
    Если счетчик не существует, создается с номером 0.

    Args:
        db (AsyncSession): Сессия базы данных.

    Returns:
        models.OfferCounter: Объект счетчика КП.
    """
    logger.info("[CRUD] get_or_create_offer_counter: получение/создание счетчика КП")
    
    # Пытаемся найти существующий счетчик
    result = await db.execute(select(models.OfferCounter).filter_by(id=0))
    counter = result.scalar_one_or_none()
    
    if not counter:
        # Создаем новый счетчик, если не найден
        counter = models.OfferCounter(id=0, current_number=0)
        db.add(counter)
        await db.commit()
        await db.refresh(counter)
        logger.info("[CRUD] get_or_create_offer_counter: создан новый счетчик с номером 0")
    else:
        logger.info(f"[CRUD] get_or_create_offer_counter: найден существующий счетчик с номером {counter.current_number}")
    
    return counter

async def increment_offer_counter(db: AsyncSession) -> int:
    """
    Увеличение счетчика номеров КП на 1 и возврат нового номера.

    Args:
        db (AsyncSession): Сессия базы данных.

    Returns:
        int: Новый номер КП.
    """
    logger.info("[CRUD] increment_offer_counter: увеличение счетчика КП")
    
    try:
        # Получаем или создаем счетчик
        counter = await get_or_create_offer_counter(db)
        
        # Увеличиваем номер
        counter.current_number += 1
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(counter)
        
        logger.info(f"[CRUD] increment_offer_counter: новый номер КП = {counter.current_number}")
        return counter.current_number
        
    except Exception as e:
        logger.error(f"[CRUD] increment_offer_counter: ошибка при увеличении счетчика: {e}", exc_info=True)
        await db.rollback()
        raise

async def get_current_offer_number(db: AsyncSession) -> int:
    """
    Получение текущего номера КП без увеличения.

    Args:
        db (AsyncSession): Сессия базы данных.

    Returns:
        int: Текущий номер КП.
    """
    logger.info("[CRUD] get_current_offer_number: получение текущего номера КП")
    
    counter = await get_or_create_offer_counter(db)
    logger.info(f"[CRUD] get_current_offer_number: текущий номер КП = {counter.current_number}")
    return counter.current_number

# --- CRUD-операции для составных заказов (ComposeOrder) ---

async def create_compose_order(db: AsyncSession, compose_order: schemas.ComposeOrderCreate) -> models.ComposeOrder:
    """
    Создание нового составного заказа.

    Args:
        db (AsyncSession): Сессия базы данных.
        compose_order (schemas.ComposeOrderCreate): Данные для создания составного заказа.

    Returns:
        models.ComposeOrder: Созданный составной заказ.
    """
    logger.info(f"[CRUD] create_compose_order: создание составного заказа для клиента id={compose_order.client_id}")
    
    try:
        db_compose_order = models.ComposeOrder(
            client_id=compose_order.client_id,
            created_at=compose_order.created_at,
            status=compose_order.status,
            pdf_path=compose_order.pdf_path,
            compose_order_data=json.dumps(compose_order.compose_order_data, ensure_ascii=False)
        )
        db.add(db_compose_order)
        await db.commit()
        await db.refresh(db_compose_order)
        logger.info(f"[CRUD] create_compose_order: составной заказ создан с id={db_compose_order.id}")
        return db_compose_order
    except Exception as e:
        logger.error(f"[CRUD] create_compose_order: ошибка при создании составного заказа: {e}", exc_info=True)
        await db.rollback()
        raise

async def get_compose_order(db: AsyncSession, compose_order_id: int) -> models.ComposeOrder:
    """
    Получение составного заказа по ID.

    Args:
        db (AsyncSession): Сессия базы данных.
        compose_order_id (int): ID составного заказа.

    Returns:
        models.ComposeOrder: Составной заказ или None.
    """
    logger.info(f"[CRUD] get_compose_order: получение составного заказа id={compose_order_id}")
    
    result = await db.execute(select(models.ComposeOrder).where(models.ComposeOrder.id == compose_order_id))
    compose_order = result.scalar_one_or_none()
    
    if compose_order:
        logger.info(f"[CRUD] get_compose_order: составной заказ id={compose_order_id} найден")
    else:
        logger.warning(f"[CRUD] get_compose_order: составной заказ id={compose_order_id} не найден")
    
    return compose_order

async def get_compose_orders(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[models.ComposeOrder]:
    """
    Получение списка составных заказов.

    Args:
        db (AsyncSession): Сессия базы данных.
        skip (int): Количество записей для пропуска.
        limit (int): Максимальное количество записей.

    Returns:
        list[models.ComposeOrder]: Список составных заказов.
    """
    logger.info(f"[CRUD] get_compose_orders: получение списка составных заказов (skip={skip}, limit={limit})")
    
    result = await db.execute(select(models.ComposeOrder).offset(skip).limit(limit))
    compose_orders = result.scalars().all()
    
    logger.info(f"[CRUD] get_compose_orders: получено {len(compose_orders)} составных заказов")
    return compose_orders

async def update_compose_order(db: AsyncSession, compose_order_id: int, compose_order_update: schemas.ComposeOrderBase) -> models.ComposeOrder:
    """
    Обновление составного заказа.

    Args:
        db (AsyncSession): Сессия базы данных.
        compose_order_id (int): ID составного заказа.
        compose_order_update (schemas.ComposeOrderBase): Данные для обновления.

    Returns:
        models.ComposeOrder: Обновленный составной заказ или None.
    """
    logger.info(f"[CRUD] update_compose_order: обновление составного заказа id={compose_order_id}")
    
    result = await db.execute(select(models.ComposeOrder).where(models.ComposeOrder.id == compose_order_id))
    db_compose_order = result.scalar_one_or_none()
    
    if not db_compose_order:
        logger.warning(f"[CRUD] update_compose_order: составной заказ id={compose_order_id} не найден")
        return None
    
    try:
        db_compose_order.status = compose_order_update.status
        db_compose_order.pdf_path = compose_order_update.pdf_path
        db_compose_order.compose_order_data = json.dumps(compose_order_update.compose_order_data, ensure_ascii=False)
        await db.commit()
        await db.refresh(db_compose_order)
        logger.info(f"[CRUD] update_compose_order: составной заказ id={compose_order_id} успешно обновлен")
        return db_compose_order
    except Exception as e:
        logger.error(f"[CRUD] update_compose_order: ошибка при обновлении составного заказа id={compose_order_id}: {e}", exc_info=True)
        await db.rollback()
        raise

async def delete_compose_order(db: AsyncSession, compose_order_id: int) -> bool:
    """
    Удаление составного заказа.

    Args:
        db (AsyncSession): Сессия базы данных.
        compose_order_id (int): ID составного заказа.

    Returns:
        bool: True если заказ удален, False если не найден.
    """
    logger.info(f"[CRUD] delete_compose_order: удаление составного заказа id={compose_order_id}")
    
    result = await db.execute(select(models.ComposeOrder).where(models.ComposeOrder.id == compose_order_id))
    db_compose_order = result.scalar_one_or_none()
    
    if not db_compose_order:
        logger.warning(f"[CRUD] delete_compose_order: составной заказ id={compose_order_id} не найден")
        return False
    
    try:
        await db.delete(db_compose_order)
        await db.commit()
        logger.info(f"[CRUD] delete_compose_order: составной заказ id={compose_order_id} успешно удален")
        return True
    except Exception as e:
        logger.error(f"[CRUD] delete_compose_order: ошибка при удалении составного заказа id={compose_order_id}: {e}", exc_info=True)
        await db.rollback()
        raise
