"""
Миграция для добавления таблицы order_components
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from utils.mylogger import Logger

logger = Logger(name=__name__, log_file="migration.log")

def run_migration():
    """Выполняет миграцию для добавления таблицы order_components"""
    
    # Получаем URL базы данных из переменной окружения или используем значение по умолчанию
    database_url = os.getenv("DATABASE_URL", "sqlite:///./aircon_commercial_offer.db")
    
    try:
        # Создаем движок базы данных
        engine = create_engine(database_url)
        
        # Создаем сессию
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        logger.info("Начало миграции: добавление таблицы order_components")
        
        # Проверяем, существует ли уже таблица order_components
        result = db.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='order_components'
        """))
        
        if result.fetchone():
            logger.info("Таблица order_components уже существует, миграция не требуется")
            return True
        
        # Создаем таблицу order_components
        db.execute(text("""
            CREATE TABLE order_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                component_id INTEGER NOT NULL,
                quantity REAL,
                length REAL,
                measurement_type VARCHAR(20) DEFAULT 'quantity',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (component_id) REFERENCES components (id)
            )
        """))
        
        # Создаем индексы для улучшения производительности
        db.execute(text("""
            CREATE INDEX idx_order_components_order_id 
            ON order_components (order_id)
        """))
        
        db.execute(text("""
            CREATE INDEX idx_order_components_component_id 
            ON order_components (component_id)
        """))
        
        # Удаляем старую таблицу связей order_component, если она существует
        result = db.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='order_component'
        """))
        
        if result.fetchone():
            logger.info("Удаление старой таблицы связей order_component")
            db.execute(text("DROP TABLE order_component"))
        
        # Фиксируем изменения
        db.commit()
        
        logger.info("Миграция успешно завершена: таблица order_components создана")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграции: {str(e)}", exc_info=True)
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ Миграция успешно выполнена")
    else:
        print("❌ Ошибка при выполнении миграции") 