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

# --- Основные модели ---

class User(Base):
    """
    Модель пользователя системы.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор пользователя
    username = Column(String, unique=True, index=True)  # Логин пользователя
    password_hash = Column(String, nullable=False)  # Хешированный пароль
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Дата создания
    last_login = Column(DateTime(timezone=True), nullable=True)  # Последний вход
    is_active = Column(Boolean, default=True)  # Активность пользователя
    current_token = Column(String, nullable=True)  # Текущий токен сессии
    token_expires_at = Column(DateTime(timezone=True), nullable=True)  # Время истечения токена

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
    compose_orders = relationship("ComposeOrder", back_populates="client")  # Связь с составными заказами клиента

class Order(Base):
    """
    Модель заказа (коммерческого предложения).
    """
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор заказа
    status = Column(String, default='draft')  # Статус заказа: 'draft' или 'ready'
    pdf_path = Column(String, nullable=True)  # Путь к PDF-файлу (если есть)
    order_data = Column(Text, nullable=False)  # Все данные заказа в формате JSON (строка)
    order_type = Column(String, default='Order')  # Тип заказа: 'Order' или 'Compose'
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
    mount_type = Column(String, nullable=True)  # Тип кондиционера
    image_path = Column(String, nullable=True)  # Путь к изображению кондиционера

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

class OfferCounter(Base):
    """
    Модель для хранения счетчика номеров коммерческих предложений.
    """
    __tablename__ = 'offer_counters'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор счетчика
    current_number = Column(Integer, default=1)  # Текущий номер КП
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # Время последнего обновления

class Room(Base):
    """
    Модель помещения (комнаты) в рамках заказа.
    Один заказ может содержать несколько помещений.
    """
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор помещения
    order_id = Column(Integer, ForeignKey('compose_orders.id'), nullable=False)  # Внешний ключ на составной заказ
    
    # Основные параметры помещения
    area = Column(Float, nullable=False)  # Площадь помещения (м²)
    room_type = Column(String, nullable=True)  # Тип помещения (текстовое поле)
    
    # Требования к кондиционеру
    brand = Column(String, nullable=True)  # Предпочитаемый бренд
    wifi = Column(Boolean, default=False)  # Поддержка Wi-Fi
    inverter = Column(Boolean, default=False)  # Инверторный тип
    price_limit = Column(Float, nullable=True)  # Верхний порог стоимости (BYN)
    mount_type = Column(String, nullable=True)  # Тип кондиционера
    
    # Параметры помещения для расчета
    ceiling_height = Column(Float, default=2.7)  # Высота потолков (м)
    illumination = Column(String, nullable=True)  # Освещенность
    num_people = Column(Integer, default=1)  # Количество людей
    activity = Column(String, nullable=True)  # Активность людей
    num_computers = Column(Integer, default=0)  # Количество компьютеров
    num_tvs = Column(Integer, default=0)  # Количество телевизоров
    other_power = Column(Float, default=0)  # Мощность прочей техники (Вт)
    
    # Дополнительная информация
    comments = Column(Text, nullable=True)  # Комментарии к помещению
    installation_price = Column(Float, default=666)  # Стоимость монтажа для этого помещения (BYN)
    selected_aircons_for_room = Column(JSONB, nullable=True)  # Выбранные кондиционеры для этого помещения (JSON)
    components_for_room = Column(JSONB, nullable=True)  # Комплектующие для этого помещения (JSON)
    
    # Системные поля
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Дата создания
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # Дата обновления
    
    # Связи
    compose_order = relationship("ComposeOrder", back_populates="rooms")  # Связь с составным заказом

class ComposeOrder(Base):
    """
    Модель составного заказа (несколько кондиционеров для одного клиента).
    """
    __tablename__ = 'compose_orders'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор составного заказа
    status = Column(String, default='draft')  # Статус заказа: 'draft' или 'ready'
    pdf_path = Column(String, nullable=True)  # Путь к PDF-файлу (если есть)
    compose_order_data = Column(Text, nullable=False)  # Все данные составного заказа в формате JSON (строка)
    order_type = Column(String, default='Compose')  # Тип заказа: 'Order' или 'Compose'
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Дата создания заказа
    client_id = Column(Integer, ForeignKey('clients.id'))  # Внешний ключ на клиента
    client = relationship("Client", back_populates="compose_orders")  # Объект клиента
    rooms = relationship("Room", back_populates="compose_order")  # Связь с помещениями

logger.info("Все модели базы данных (Client, Order, AirConditioner, Component, OfferCounter, Room с полями installation_price и components_for_room, ComposeOrder) успешно определены.")