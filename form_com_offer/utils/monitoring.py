"""
Модуль автоматического мониторинга состояния приложения
"""
import asyncio
import time
import psutil
from typing import Dict, Any
from utils.mylogger import Logger

logger = Logger(name="monitoring", log_file="monitoring.log")

class ApplicationMonitor:
    """Класс для мониторинга состояния приложения"""
    
    def __init__(self):
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 минут между алертами
        self.monitoring_active = False
        self._monitor_task = None  # Ссылка на задачу мониторинга
        
    async def start_monitoring(self):
        """Запуск автоматического мониторинга"""
        # Проверяем, не запущен ли уже мониторинг
        if self.monitoring_active and self._monitor_task and not self._monitor_task.done():
            logger.warning("Мониторинг уже запущен")
            return
            
        # Если есть старая задача, отменяем её
        if self._monitor_task and not self._monitor_task.done():
            logger.info("Отмена предыдущей задачи мониторинга")
            self._monitor_task.cancel()
            try:
                await asyncio.wait_for(self._monitor_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            self._monitor_task = None
            
        self.monitoring_active = True
        logger.info("🚀 Автоматический мониторинг приложения запущен")
        
        # Создаем и сохраняем задачу мониторинга
        self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self):
        """Остановка автоматического мониторинга"""
        self.monitoring_active = False
        
        # Отменяем задачу мониторинга, если она существует
        if self._monitor_task and not self._monitor_task.done():
            logger.info("Отмена задачи мониторинга")
            self._monitor_task.cancel()
            
            try:
                # Ждем завершения задачи с таймаутом
                await asyncio.wait_for(self._monitor_task, timeout=10.0)
                logger.info("Задача мониторинга успешно завершена")
            except asyncio.CancelledError:
                logger.info("Задача мониторинга была отменена")
            except asyncio.TimeoutError:
                logger.warning("Таймаут ожидания завершения задачи мониторинга")
            except Exception as e:
                logger.error(f"Ошибка при ожидании завершения задачи мониторинга: {e}")
            finally:
                self._monitor_task = None
        
        logger.info("🛑 Автоматический мониторинг приложения остановлен")
    
    async def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.monitoring_active:
            try:
                await self._check_system_health()
                await self._check_database_health()
                await self._check_connection_pool()
                
                # Пауза между проверками
                await asyncio.sleep(60)  # Проверяем каждую минуту
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(30)  # При ошибке проверяем через 30 секунд
    
    async def _check_system_health(self):
        """Проверка системного здоровья"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Проверяем критические пороги
            if cpu_percent > 80:
                await self._send_alert("system", f"Высокая загрузка CPU: {cpu_percent}%")
            
            if memory.percent > 85:
                await self._send_alert("system", f"Высокое потребление памяти: {memory.percent}%")
            
            if disk.percent > 90:
                await self._send_alert("system", f"Критическое заполнение диска: {disk.percent}%")
                
        except Exception as e:
            logger.error(f"Ошибка проверки системного здоровья: {e}")
    
    async def _check_database_health(self):
        """Проверка здоровья базы данных"""
        try:
            from db.database import AsyncSessionLocal
            from sqlalchemy import text
            
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
                
        except Exception as e:
            await self._send_alert("database", f"Ошибка подключения к БД: {e}")
    
    async def _check_connection_pool(self):
        """Проверка состояния пула соединений"""
        try:
            from db.database import engine
            pool = engine.pool
            
            pool_size = pool.size()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            utilization = (checked_out / pool_size * 100) if pool_size > 0 else 0
            
            # Проверяем критические условия
            if utilization > 90:
                await self._send_alert("pool", f"Высокая утилизация пула: {utilization:.1f}%")
            
            if overflow > 5:
                await self._send_alert("pool", f"Переполнение пула: {overflow} соединений")
            
            if checked_out == pool_size:
                await self._send_alert("pool", "Все соединения в пуле заняты!")
                
        except Exception as e:
            logger.error(f"Ошибка проверки пула соединений: {e}")
    
    async def _send_alert(self, alert_type: str, message: str):
        """Отправка алерта с защитой от спама"""
        current_time = time.time()
        alert_key = f"{alert_type}_{message}"
        
        # Проверяем, не отправляли ли мы недавно такой же алерт
        if alert_key in self.last_alert_time:
            if current_time - self.last_alert_time[alert_key] < self.alert_cooldown:
                return
        
        # Логируем алерт
        logger.warning(f"🚨 АЛЕРТ [{alert_type.upper()}]: {message}")
        self.last_alert_time[alert_key] = current_time
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Получение текущего статуса здоровья приложения"""
        try:
            # Системная информация
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Информация о пуле соединений
            pool_stats = {}
            try:
                from db.database import engine
                pool = engine.pool
                pool_stats = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "utilization_percent": round((pool.checkedout() / pool.size()) * 100, 2) if pool.size() > 0 else 0
                }
            except Exception as e:
                pool_stats = {"error": str(e)}
            
            # Статус базы данных
            db_status = "healthy"
            try:
                from db.database import AsyncSessionLocal
                from sqlalchemy import text
                async with AsyncSessionLocal() as session:
                    await session.execute(text("SELECT 1"))
            except Exception as e:
                db_status = f"error: {str(e)}"
            
            # Определяем общий статус
            overall_status = "healthy"
            if (cpu_percent > 80 or memory.percent > 85 or 
                disk.percent > 90 or db_status != "healthy" or
                pool_stats.get("utilization_percent", 0) > 90):
                overall_status = "warning"
            
            if (cpu_percent > 95 or memory.percent > 95 or 
                disk.percent > 95 or db_status != "healthy" or
                pool_stats.get("utilization_percent", 0) > 95):
                overall_status = "critical"
            
            return {
                "timestamp": time.time(),
                "overall_status": overall_status,
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                    "disk_usage_percent": disk.percent
                },
                "database_status": db_status,
                "pool_stats": pool_stats
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса здоровья: {e}")
            return {
                "timestamp": time.time(),
                "overall_status": "error",
                "error": str(e)
            }

# Глобальный экземпляр монитора
monitor = ApplicationMonitor()
