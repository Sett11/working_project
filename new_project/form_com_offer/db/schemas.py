from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import date

# --- Base Schemas ---
# Общая конфигурация для всех схем, которые читают данные из БД
class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- Component Schemas ---
class ComponentBase(BaseModel):
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
    pass

class Component(ComponentBase, OrmBase):
    id: int

# --- AirConditioner Schemas ---
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

class AirConditionerCreate(AirConditionerBase):
    pass

class AirConditioner(AirConditionerBase, OrmBase):
    id: int

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    role: str

class UserCreate(UserBase):
    password: str

class User(UserBase, OrmBase):
    id: int

# --- Client Schemas ---
class ClientBase(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class Client(ClientBase, OrmBase):
    id: int

# --- Order Schemas ---
class OrderBase(BaseModel):
    status: Optional[str] = "forming"
    discount: Optional[int] = 0
    room_type: Optional[str] = None
    room_area: Optional[float] = None
    installer_data: Optional[dict] = None # Для данных от монтажника

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

# --- Схемы для эндпоинта генерации КП ---
class CommercialOfferPayload(BaseModel):
    client_data: ClientCreate
    order_params: dict # area, type_room, discount
    aircon_params: dict # wifi, inverter, price_limit, brand