from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

# Таблица для связи "многие-ко-многим" между Заказами и Кондиционерами
class OrderAirConditioner(Base):
    __tablename__ = 'order_air_conditioners'
    order_id = Column(Integer, ForeignKey('orders.id'), primary_key=True)
    air_conditioner_id = Column(Integer, ForeignKey('air_conditioners.id'), primary_key=True)
    quantity = Column(Integer, default=1)

# Таблица для связи "многие-ко-многим" между Заказами и Комплектующими
class OrderComponent(Base):
    __tablename__ = 'order_components'
    order_id = Column(Integer, ForeignKey('orders.id'), primary_key=True)
    component_id = Column(Integer, ForeignKey('components.id'), primary_key=True)
    quantity = Column(Integer, default=1)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # "manager", "installer", "admin"
    orders = relationship("Order", back_populates="manager")

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    phone = Column(String, unique=True)
    email = Column(String, unique=True, nullable=True)
    address = Column(String)
    orders = relationship("Order", back_populates="client")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    created_date = Column(Date)
    visit_date = Column(Date, nullable=True)
    status = Column(String, default="forming") # "forming", "formed", "closed"
    room_type = Column(String)
    room_area = Column(Float)
    discount = Column(Integer, default=0)
    
    client_id = Column(Integer, ForeignKey("clients.id"))
    client = relationship("Client", back_populates="orders")

    manager_id = Column(Integer, ForeignKey("users.id"))
    manager = relationship("User", back_populates="orders")

    # Связи многие-ко-многим
    air_conditioners = relationship("AirConditioner", secondary="order_air_conditioners", back_populates="orders")
    components = relationship("Component", secondary="order_components", back_populates="orders")


class AirConditioner(Base):
    __tablename__ = "air_conditioners"
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, index=True)
    model = Column(String, unique=True, index=True)
    series = Column(String)
    power_btu = Column(Integer)
    power_kw = Column(Float)
    room_area = Column(Float)
    price = Column(Float)
    noise_level = Column(String, nullable=True)
    energy_efficiency_class = Column(String, nullable=True)
    has_inverter = Column(Boolean, default=False)
    has_wifi = Column(Boolean, default=False)
    image_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    
    orders = relationship("Order", secondary="order_air_conditioners", back_populates="air_conditioners")


class Component(Base):
    __tablename__ = "components"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    unit = Column(String)
    price = Column(Float)

    orders = relationship("Order", secondary="order_components", back_populates="components")
