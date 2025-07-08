from sqlalchemy import (Column, Integer, String, Float, Boolean, Date, ForeignKey,
                        Text, JSON)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# --- Ассоциативные таблицы для связей многие-ко-многим ---

class OrderAirConditioner(Base):
    __tablename__ = 'order_air_conditioners'
    order_id = Column(Integer, ForeignKey('orders.id'), primary_key=True)
    air_conditioner_id = Column(Integer, ForeignKey('air_conditioners.id'), primary_key=True)
    quantity = Column(Integer, default=1)
    price_at_moment = Column(Float) # Цена на момент добавления в заказ

class OrderComponent(Base):
    __tablename__ = 'order_components'
    order_id = Column(Integer, ForeignKey('orders.id'), primary_key=True)
    component_id = Column(Integer, ForeignKey('components.id'), primary_key=True)
    quantity = Column(Integer, default=1)
    price_at_moment = Column(Float) # Цена на момент добавления в заказ

# --- Основные таблицы ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "manager", "installer", "admin"
    
    # Связь: один менеджер может создать много заказов
    created_orders = relationship("Order", back_populates="manager")

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    phone = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    address = Column(Text, nullable=True)
    
    # Связь: один клиент может иметь много заказов
    orders = relationship("Order", back_populates="client")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="forming")  # "forming", "formed", "closed"
    created_at = Column(Date, nullable=False)
    visit_date = Column(Date, nullable=True)
    discount = Column(Integer, default=0)
    
    # Внешние ключи
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Параметры, которые вводит менеджер
    room_type = Column(String)
    room_area = Column(Float)
    
    # Параметры, которые вводит монтажник (можно хранить в JSON)
    installer_data = Column(JSON, nullable=True)
    
    # Путь к сгенерированному PDF
    pdf_path = Column(String, nullable=True)

    # Связи
    client = relationship("Client", back_populates="orders")
    manager = relationship("User", back_populates="created_orders")
    air_conditioners = relationship("AirConditioner", secondary="order_air_conditioners", back_populates="orders")
    components = relationship("Component", secondary="order_components", back_populates="orders")

class AirConditioner(Base):
    __tablename__ = "air_conditioners"
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String, unique=True, index=True, nullable=False)
    brand = Column(String, index=True)
    series = Column(String, nullable=True)
    
    # Технические характеристики из 'specifications'
    cooling_power_kw = Column(Float, nullable=True)
    heating_power_kw = Column(Float, nullable=True)
    cooling_consumption_kw = Column(Float, nullable=True)
    heating_consumption_kw = Column(Float, nullable=True)
    pipe_diameter = Column(String, nullable=True)
    energy_efficiency_class = Column(String, nullable=True)
    
    # Цены из 'pricing'
    dealer_price_usd = Column(Float, nullable=True)
    retail_price_usd = Column(Float, nullable=True)
    retail_price_byn = Column(Float, nullable=True)
    
    # Остальные поля
    description = Column(Text, nullable=True)
    air_description = Column(Text, nullable=True)
    representative_image = Column(String, nullable=True)
    
    # Связь с заказами
    orders = relationship("Order", secondary="order_air_conditioners", back_populates="air_conditioners")

class Component(Base):
    __tablename__ = "components"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, nullable=False)
    category = Column(String, index=True)
    size = Column(String, nullable=True)
    material = Column(String, nullable=True)
    characteristics = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String, default="BYN")
    standard = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    in_stock = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    
    # Связь с заказами
    orders = relationship("Order", secondary="order_components", back_populates="components")