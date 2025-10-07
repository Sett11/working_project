"""
Модуль Pydantic-схем для сериализации и валидации данных между API и БД.
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Union
from datetime import date, datetime
from decimal import Decimal
from utils.mylogger import Logger
from .models import OrderStatus

logger = Logger(name=__name__, log_file="db.log")

class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- Component Schemas (СКОРРЕКТИРОВАНО) ---
class ComponentBase(BaseModel):
    name: str
    category: str
    price: Optional[Union[float, Decimal]] = None  # Поддержка Decimal и float для совместимости
    size: Optional[str] = None
    material: Optional[str] = None  # Сделано опциональным
    characteristics: Optional[str] = None
    currency: Optional[str] = "BYN"
    standard: Optional[str] = None  # Сделано опциональным
    manufacturer: Optional[str] = None
    in_stock: Optional[bool] = True
    description: Optional[str] = None
    image_url: Optional[str] = None

class ComponentCreate(ComponentBase):
    pass

class Component(ComponentBase, OrmBase):
    id: int

# --- Остальные схемы без изменений ---
class AirConditionerBase(BaseModel):
    model_name: str
    brand: Optional[str] = None
    series: Optional[str] = None
    cooling_power_kw: Optional[float] = None
    energy_efficiency_class: Optional[str] = None
    retail_price_byn: Optional[Union[float, Decimal]] = None  # Поддержка Decimal и float для совместимости
    description: Optional[str] = None
    is_inverter: Optional[bool] = False
    has_wifi: Optional[bool] = False
    mount_type: Optional[str] = None
    image_path: Optional[str] = None

class AirConditionerCreate(AirConditionerBase):
    pass

class AirConditioner(AirConditionerBase, OrmBase):
    id: int

# --- User Schemas ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    secret_key: Optional[str] = None  # Сделано опциональным для гибкости
    email: Optional[str] = None  # Добавлено поле email

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase, OrmBase):
    id: int
    email: Optional[str] = None  # Добавлено поле email
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool
    is_admin: Optional[bool] = False

class TokenResponse(BaseModel):
    """Схема для ответа при аутентификации (login/register)"""
    token: str  # JWT токен
    expires_at: str  # ISO format datetime string для совместимости с frontend
    user: UserResponse  # Полная информация о пользователе

class ClientBase(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class Client(ClientBase, OrmBase):
    id: int


class OfferCounterBase(BaseModel):
    current_number: int

class OfferCounterCreate(OfferCounterBase):
    pass

class OfferCounter(OfferCounterBase, OrmBase):
    id: int
    updated_at: Optional[date] = None

# --- Новая схема для составных заказов ---
class ComposeOrderBase(BaseModel):
    status: Optional[Union[OrderStatus, str]] = "draft"  # Поддержка Enum и строк для обратной совместимости
    pdf_path: Optional[str] = None
    compose_order_data: dict  # Данные составного заказа
    order_type: Optional[str] = "Compose"

class ComposeOrderCreate(ComposeOrderBase):
    user_id: int
    client_id: int
    created_at: date

class ComposeOrder(ComposeOrderBase, OrmBase):
    id: int
    created_at: date
    client: Client

class ComposeOrderPayload(BaseModel):
    client_data: ClientCreate
    airs: list  # Список кондиционеров с автоинкрементными ID
    components: list  # Комплектующие для всего заказа
    status: Optional[Union[OrderStatus, str]] = "draft"  # Поддержка Enum и строк для обратной совместимости

logger.info("Pydantic-схемы успешно определены.")