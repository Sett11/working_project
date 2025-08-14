"""
Модуль Pydantic-схем для сериализации и валидации данных между API и БД.
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date
from utils.mylogger import Logger

logger = Logger(name=__name__, log_file="db.log")

class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- Component Schemas (СКОРРЕКТИРОВАНО) ---
class ComponentBase(BaseModel):
    name: str
    category: str
    price: Optional[float] = None
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
    retail_price_byn: Optional[float] = None
    description: Optional[str] = None
    is_inverter: Optional[bool] = False
    has_wifi: Optional[bool] = False
    mount_type: Optional[str] = None

class AirConditionerCreate(AirConditionerBase):
    pass

class AirConditioner(AirConditionerBase, OrmBase):
    id: int

# УДАЛЕНО: UserBase, UserCreate, User

class ClientBase(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class Client(ClientBase, OrmBase):
    id: int

class OrderBase(BaseModel):
    status: Optional[str] = "draft"
    pdf_path: Optional[str] = None
    order_data: dict

class OrderCreate(OrderBase):
    client_id: int
    created_at: date

class Order(OrderBase, OrmBase):
    id: int
    created_at: date
    client: Client

class CommercialOfferPayload(BaseModel):
    client_data: ClientCreate
    order_params: dict
    aircon_params: dict

class FullOrderCreate(BaseModel):
    id: Optional[int] = None
    client_data: ClientCreate
    order_params: dict
    aircon_params: dict
    components: list
    status: Optional[str] = "draft"

class OfferCounterBase(BaseModel):
    current_number: int

class OfferCounterCreate(OfferCounterBase):
    pass

class OfferCounter(OfferCounterBase, OrmBase):
    id: int
    updated_at: Optional[date] = None

logger.info("Pydantic-схемы успешно определены.")