"""
Модуль Pydantic-схем для сериализации и валидации данных между API и БД.

Здесь определены схемы для:
- Component (Комплектующее)
- AirConditioner (Кондиционер)
- User (Пользователь)
- Client (Клиент)
- Order (Заказ)
- Payload для генерации коммерческого предложения
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import date
from utils.mylogger import Logger

# Инициализация логгера для схем.
# log_file указывается без папки logs, чтобы использовать дефолтную директорию логов.
logger = Logger(name=__name__, log_file="db.log")

# --- Base Schemas ---
# Общая конфигурация для всех схем, которые читают данные из БД
class OrmBase(BaseModel):
    """
    Базовая схема для поддержки from_orm.
    """
    model_config = ConfigDict(from_attributes=True)

# --- Component Schemas ---
class ComponentBase(BaseModel):
    """
    Базовая схема комплектующего.
    """
    name: str
    category: str
    price: Optional[float] = None
    size: Optional[str] = None
    material: Optional[str] = None
    characteristics: Optional[str] = None
    currency: Optional[str] = "BYN"
    standard: Optional[str] = None
    manufacturer: Optional[str] = None
    in_stock: Optional[bool] = True
    description: Optional[str] = None
    image_url: Optional[str] = None

class ComponentCreate(ComponentBase):
    """
    Схема для создания комплектующего.
    """
    pass

class Component(ComponentBase, OrmBase):
    """
    Схема для чтения комплектующего из БД.
    """
    id: int

# --- AirConditioner Schemas ---
class AirConditionerBase(BaseModel):
    """
    Базовая схема кондиционера.
    """
    model_name: str
    brand: Optional[str] = None
    series: Optional[str] = None
    cooling_power_kw: Optional[float] = None
    heating_power_kw: Optional[float] = None
    pipe_diameter: Optional[str] = None
    energy_efficiency_class: Optional[str] = None
    retail_price_byn: Optional[float] = None
    description: Optional[str] = None
    air_description: Optional[str] = None
    representative_image: Optional[str] = None
    is_inverter: Optional[bool] = False
    has_wifi: Optional[bool] = False
    mount_type: Optional[str] = None

class AirConditionerCreate(AirConditionerBase):
    """
    Схема для создания кондиционера.
    """
    pass

class AirConditioner(AirConditionerBase, OrmBase):
    """
    Схема для чтения кондиционера из БД.
    """
    id: int

# --- User Schemas ---
class UserBase(BaseModel):
    """
    Базовая схема пользователя.
    """
    username: str
    role: str

class UserCreate(UserBase):
    """
    Схема для создания пользователя.
    """
    password: str

class User(UserBase, OrmBase):
    """
    Схема для чтения пользователя из БД.
    """
    id: int

# --- Client Schemas ---
class ClientBase(BaseModel):
    """
    Базовая схема клиента.
    """
    full_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

class ClientCreate(ClientBase):
    """
    Схема для создания клиента.
    """
    pass

class Client(ClientBase, OrmBase):
    """
    Схема для чтения клиента из БД.
    """
    id: int

# --- Order Schemas ---
class OrderBase(BaseModel):
    """
    Базовая схема заказа.
    """
    status: Optional[str] = "forming"
    discount: Optional[int] = 0
    room_type: Optional[str] = None
    room_area: Optional[float] = None
    installer_data: Optional[dict] = None # Для данных от монтажника

class OrderCreate(OrderBase):
    """
    Схема для создания заказа.
    """
    client_id: int
    manager_id: int
    created_at: date
    visit_date: Optional[date] = None

class Order(OrderBase, OrmBase):
    """
    Схема для чтения заказа из БД.
    """
    id: int
    created_at: date
    visit_date: Optional[date] = None
    client: Client
    manager: User
    air_conditioners: List[AirConditioner] = []
    components: List[Component] = []
    pdf_path: Optional[str] = None

# --- Схемы для эндпоинта генерации КП ---
class CommercialOfferPayload(BaseModel):
    """
    Схема payload для эндпоинта генерации КП.
    """
    client_data: ClientCreate
    order_params: dict # area, type_room, discount
    aircon_params: dict # wifi, inverter, price_limit, brand

logger.info("Pydantic-схемы успешно определены.")
