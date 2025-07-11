"""
Модуль моделей SQLAlchemy для работы с основной структурой базы данных.

Здесь определены таблицы и связи:
- User (Пользователь)
- Client (Клиент)
- Order (Заказ)
- AirConditioner (Кондиционер)
- Component (Комплектующее)
- Ассоциативные таблицы для связей многие-ко-многим
"""
from sqlalchemy import (Column, Integer, String, Float, ForeignKey, DateTime,
                        Text, Table, Boolean)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from utils.mylogger import Logger

# Инициализация логгера для моделей базы данных.
# log_file указывается без папки logs, чтобы использовать дефолтную директорию логов.
logger = Logger(name=__name__, log_file="db.log")

# --- Таблицы связей (Многие-ко-многим) ---

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
    """
    Модель пользователя системы.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор пользователя
    username = Column(String, unique=True, index=True)  # Имя пользователя (логин)
    hashed_password = Column(String)  # Хешированный пароль
    role = Column(String)  # Например, 'manager', 'installer'
    orders = relationship("Order", back_populates="manager")  # Связь с заказами, где пользователь — менеджер


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
    status = Column(String, default='forming')  # Статус заказа
    discount = Column(Integer, default=0)  # Скидка по заказу
    room_type = Column(String, nullable=True)  # Тип помещения
    room_area = Column(Float, nullable=True)  # Площадь помещения
    installer_data = Column(Text, nullable=True)  # Можно хранить JSON как текст (данные от монтажника)
    pdf_path = Column(String, nullable=True)  # Путь к сгенерированному PDF (если есть)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Дата создания заказа
    visit_date = Column(DateTime(timezone=True), nullable=True)  # Дата визита монтажника

    # --- Связи ---
    client_id = Column(Integer, ForeignKey('clients.id'))  # Внешний ключ на клиента
    client = relationship("Client", back_populates="orders")  # Объект клиента

    manager_id = Column(Integer, ForeignKey('users.id'))  # Внешний ключ на менеджера
    manager = relationship("User", back_populates="orders")  # Объект менеджера

    air_conditioners = relationship("AirConditioner", secondary=order_air_conditioner_association)  # Модели кондиционеров в заказе
    components = relationship("Component", secondary=order_component_association)  # Комплектующие в заказе


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
    heating_power_kw = Column(Float, nullable=True)  # Мощность обогрева (кВт)
    pipe_diameter = Column(String, nullable=True)  # Диаметр труб
    energy_efficiency_class = Column(String, nullable=True)  # Класс энергоэффективности
    retail_price_byn = Column(Float, nullable=True)  # Розничная цена (BYN)
    description = Column(Text, nullable=True)  # Описание
    air_description = Column(Text, nullable=True)  # Описание для подбора
    representative_image = Column(String, nullable=True)  # Путь к изображению
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
    in_stock = Column(String, default=True)  # В наличии
    description = Column(Text, nullable=True)  # Описание
    image_url = Column(String, nullable=True)  # Путь к изображению


logger.info("Все модели базы данных (User, Client, Order, AirConditioner, Component) успешно определены.")
