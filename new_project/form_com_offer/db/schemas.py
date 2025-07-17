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
    pass

class AirConditioner(AirConditionerBase, OrmBase):
    id: int

class UserBase(BaseModel):
    username: str
    role: str

class UserCreate(UserBase):
    password: str

class User(UserBase, OrmBase):
    id: int

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
    status: Optional[str] = "forming"
    discount: Optional[int] = 0
    room_type: Optional[str] = None
    room_area: Optional[float] = None
    installer_data: Optional[dict] = None

class OrderCreate(OrderBase):
    client_id: int
    manager_id: int
    created_at: date
    visit_date: Optional[date] = None

class Order(OrderBase, OrmBase):
    id: int
    created_at: date
    visit_date: Optional[date] = None
    client: Client
    manager: User
    air_conditioners: List[AirConditioner] = []
    components: List[Component] = []
    pdf_path: Optional[str] = None

class CommercialOfferPayload(BaseModel):
    client_data: ClientCreate
    order_params: dict
    aircon_params: dict

class FullOrderCreate(BaseModel):
    client_data: ClientCreate
    order_params: dict
    aircon_params: dict
    components: list
    status: Optional[str] = "draft"

logger.info("Pydantic-схемы успешно определены.")