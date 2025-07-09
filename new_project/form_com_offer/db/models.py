from sqlalchemy import (Column, Integer, String, Float, ForeignKey, DateTime,
                        Text, Table)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from utils.mylogger import Logger

# Инициализация логгера
logger = Logger(name=__name__, log_file="db.log")

# --- Таблицы связей (Мно��ие-ко-многим) ---

order_air_conditioner_association = Table(
    'order_air_conditioner', Base.metadata,
    Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
    Column('air_conditioner_id', Integer, ForeignKey('air_conditioners.id'), primary_key=True)
)

order_component_association = Table(
    'order_component', Base.metadata,
    Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
    Column('component_id', Integer, ForeignKey('components.id'), primary_key=True)
)


# --- Основные модели ---

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # Например, 'manager', 'installer'
    orders = relationship("Order", back_populates="manager")


class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    phone = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    orders = relationship("Order", back_populates="client")


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default='forming')
    discount = Column(Integer, default=0)
    room_type = Column(String, nullable=True)
    room_area = Column(Float, nullable=True)
    installer_data = Column(Text, nullable=True)  # Можно хранить JSON как текст
    pdf_path = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    visit_date = Column(DateTime(timezone=True), nullable=True)

    # --- Связи ---
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship("Client", back_populates="orders")

    manager_id = Column(Integer, ForeignKey('users.id'))
    manager = relationship("User", back_populates="orders")

    air_conditioners = relationship("AirConditioner", secondary=order_air_conditioner_association)
    components = relationship("Component", secondary=order_component_association)


class AirConditioner(Base):
    __tablename__ = 'air_conditioners'
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, unique=True, index=True)
    brand = Column(String, index=True, nullable=True)
    series = Column(String, nullable=True)
    cooling_power_kw = Column(Float, nullable=True)
    heating_power_kw = Column(Float, nullable=True)
    pipe_diameter = Column(String, nullable=True)
    energy_efficiency_class = Column(String, nullable=True)
    retail_price_byn = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    air_description = Column(Text, nullable=True)
    representative_image = Column(String, nullable=True)


class Component(Base):
    __tablename__ = 'components'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    price = Column(Float, nullable=True)
    size = Column(String, nullable=True)
    material = Column(String, nullable=True)
    characteristics = Column(String, nullable=True)
    currency = Column(String, default="BYN")
    standard = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    in_stock = Column(String, default=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)


logger.info("Все модели базы данных (User, Client, Order, AirConditioner, Component) успешно определены.")
