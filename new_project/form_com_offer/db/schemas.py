from pydantic import BaseModel
from typing import List, Optional
from datetime import date

# --- Component Schemas ---
class ComponentBase(BaseModel):
    name: str
    unit: str
    price: float

class ComponentCreate(ComponentBase):
    pass

class Component(ComponentBase):
    id: int

    class Config:
        orm_mode = True

# --- AirConditioner Schemas ---
class AirConditionerBase(BaseModel):
    brand: str
    model: str
    series: str
    power_btu: int
    power_kw: float
    room_area: float
    price: float
    noise_level: Optional[str] = None
    energy_efficiency_class: Optional[str] = None
    has_inverter: bool = False
    has_wifi: bool = False
    image_url: Optional[str] = None
    description: Optional[str] = None

class AirConditionerCreate(AirConditionerBase):
    pass

class AirConditioner(AirConditionerBase):
    id: int

    class Config:
        orm_mode = True

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    role: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        orm_mode = True

# --- Client Schemas ---
class ClientBase(BaseModel):
    full_name: str
    phone: str
    address: str
    email: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class Client(ClientBase):
    id: int

    class Config:
        orm_mode = True

# --- Order Schemas ---
class OrderBase(BaseModel):
    room_type: str
    room_area: float
    discount: Optional[int] = 0
    visit_date: Optional[date] = None
    status: Optional[str] = "forming"

class OrderCreate(OrderBase):
    client_id: int
    manager_id: int

class Order(OrderBase):
    id: int
    created_date: date
    client: Client
    manager: User
    air_conditioners: List[AirConditioner] = []
    components: List[Component] = []

    class Config:
        orm_mode = True
