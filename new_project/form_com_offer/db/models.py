"""
Модуль моделей SQLAlchemy для работы с основной структурой базы данных.

Здесь определены таблицы и связи:
- Client (Клиент)
- Order (Заказ)
- AirConditioner (Кондиционер)
- Component (Комплектующее)
- Ассоциативные таблицы для связей многие-ко-многим
"""
from sqlalchemy import (Column, Integer, String, Float, ForeignKey, DateTime,
                        Text, Table, Boolean)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from utils.mylogger import Logger

# Инициализация логгера для моделей базы данных.
# log_file указывается без папки logs, чтобы использовать дефолтную директорию логов.
logger = Logger(name=__name__, log_file="db.log")

# --- Таблицы связей (Многие-ко-многим) ---

# УДАЛЕНО: order_air_conditioner_association, order_component_association

# --- Основные модели ---

# УДАЛЕНО: class User

class Client(Base):
    """
    Модель клиента (заказчика).
    """
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор клиента
    full_name = Column(String, index=True)  # ФИО клиента
    phone = Column(String, unique=True, index=True)  # Телефон клиента
    email = Column(String, nullable=True)  # Email клиента
    address = Column(String, nullable=True)  # Адрес клиента
    orders = relationship("Order", back_populates="client")  # Связь с заказами клиента

class Order(Base):
    """
    Модель заказа (коммерческого предложения).
    """
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор заказа
    status = Column(String, default='draft')  # Статус заказа: 'draft' или 'ready'
    pdf_path = Column(String, nullable=True)  # Путь к PDF-файлу (если есть)
    order_data = Column(Text, nullable=False)  # Все данные заказа в формате JSON (строка)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Дата создания заказа
    client_id = Column(Integer, ForeignKey('clients.id'))  # Внешний ключ на клиента
    client = relationship("Client", back_populates="orders")  # Объект клиента

class AirConditioner(Base):
    """
    Модель кондиционера.
    """
    __tablename__ = 'air_conditioners'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор кондиционера
    model_name = Column(String, unique=True, index=True)  # Модель кондиционера
    brand = Column(String, index=True, nullable=True)  # Бренд
    series = Column(String, nullable=True)  # Серия
    cooling_power_kw = Column(Float, nullable=True)  # Мощность охлаждения (кВт)
    energy_efficiency_class = Column(String, nullable=True)  # Класс энергоэффективности
    retail_price_byn = Column(Float, nullable=True)  # Розничная цена (BYN)
    description = Column(Text, nullable=True)  # Описание
    is_inverter = Column(Boolean, default=False)  # Признак инверторного компрессора
    has_wifi = Column(Boolean, default=False)  # Признак наличия Wi-Fi
    mount_type = Column(String, nullable=True)  # Тип монтажа

class Component(Base):
    """
    Модель комплектующего для монтажа.
    """
    __tablename__ = 'components'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор комплектующего
    name = Column(String, index=True)  # Название комплектующего
    category = Column(String, index=True)  # Категория
    price = Column(Float, nullable=True)  # Цена
    size = Column(String, nullable=True)  # Размер
    material = Column(String, nullable=True)  # Материал
    characteristics = Column(String, nullable=True)  # Характеристики
    currency = Column(String, default="BYN")  # Валюта
    standard = Column(String, nullable=True)  # Стандарт
    manufacturer = Column(String, nullable=True)  # Производитель
    in_stock = Column(Boolean, default=True)  # В наличии
    description = Column(Text, nullable=True)  # Описание
    image_url = Column(String, nullable=True)  # Путь к изображению

logger.info("Все модели базы данных (Client, Order, AirConditioner, Component) успешно определены.")