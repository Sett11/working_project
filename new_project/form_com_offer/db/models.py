from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from utils.mylogger import Logger

# Инициализация логгера
logger = Logger(name=__name__, log_file="db.log")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, index=True)
    customer_address = Column(String)
    customer_phone = Column(String)
    customer_email = Column(String)
    customer_telegram = Column(String)
    room_type = Column(String)
    area = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    visit_date = Column(DateTime(timezone=True))
    status = Column(String, default='forming')
    discount = Column(Float, default=0.0)
    # Связь с коммерческим предложением (если оно хранится отдельно)
    # commercial_offer_id = Column(Integer, ForeignKey('commercial_offers.id'))
    # commercial_offer = relationship("CommercialOffer")

class AirConditioner(Base):
    __tablename__ = 'air_conditioners'
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, index=True)
    model = Column(String, unique=True, index=True)
    power_consumption = Column(String)
    cooling_capacity_btu = Column(Integer)
    cooling_capacity_kw = Column(Float)
    heating_capacity_btu = Column(Integer)
    heating_capacity_kw = Column(Float)
    inverter = Column(String)
    noise_level_indoor = Column(String)
    noise_level_outdoor = Column(String)
    price = Column(Float)
    image_url = Column(String)
    description = Column(Text)

class Component(Base):
    __tablename__ = 'components'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String, index=True)
    characteristics = Column(String)
    price = Column(Float)
    image_url = Column(String)
    description = Column(Text)

logger.info("Модели базы данных (Order, AirConditioner, Component) успешно определены.")
