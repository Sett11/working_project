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
        """Основной цикл мониторинга (оптимизирован для снижения нагрузки на CPU)"""
        while self.monitoring_active:
            try:
                await self._check_system_health()
                await self._check_database_health()
                await self._check_connection_pool()
                await self._check_graceful_degradation()
                
                # Пауза между проверками (увеличена для снижения нагрузки)
                await asyncio.sleep(300)  # Проверяем каждые 5 минут (увеличено с 1 минуты)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # При ошибке проверяем через 1 минуту (увеличено с 30 секунд)
    
    async def _check_system_health(self):
        """Проверка системного здоровья"""
        try:
            # Используем мгновенные значения без блокирующих вызовов
            cpu_percent = psutil.cpu_percent(interval=None)  # Мгновенное значение без ожидания
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
        """Проверка здоровья базы данных с таймаутом и гарантированным закрытием сессии"""
        session = None
        try:
            from db.database import AsyncSessionLocal
            from sqlalchemy import text
            
            session = AsyncSessionLocal()
            # Используем таймаут для предотвращения зависания
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=5.0)
                
        except asyncio.TimeoutError:
            await self._send_alert("database", "Таймаут подключения к БД (5 секунд)")
        except Exception as e:
            await self._send_alert("database", f"Ошибка подключения к БД: {e}")
        finally:
            # Гарантированно закрываем сессию
            if session:
                try:
                    await session.close()
                except Exception as e:
                    logger.error(f"Ошибка при закрытии сессии БД: {e}")
    
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
    
    async def _check_graceful_degradation(self):
        """Проверка состояния graceful degradation"""
        try:
            from utils.graceful_degradation import graceful_manager
            
            # Получаем статус graceful degradation
            gd_status = graceful_manager.get_degradation_status()
            
            # Проверяем, находимся ли в режиме degradation
            if gd_status.get('degradation_mode', False):
                degradation_duration = gd_status.get('degradation_duration', 0)
                recovery_attempts = gd_status.get('recovery_attempts', 0)
                max_attempts = gd_status.get('max_recovery_attempts', 5)
                
                # Алерт если degradation длится более 10 минут
                if degradation_duration > 600:  # 10 минут
                    await self._send_alert("graceful_degradation", 
                        f"Длительный режим graceful degradation: {degradation_duration:.0f} секунд")
                
                # Алерт если исчерпаны попытки восстановления
                if recovery_attempts >= max_attempts:
                    await self._send_alert("graceful_degradation", 
                        f"Исчерпаны попытки восстановления: {recovery_attempts}/{max_attempts}")
                
                # Алерт если degradation длится более 30 минут
                if degradation_duration > 1800:  # 30 минут
                    await self._send_alert("graceful_degradation", 
                        f"Критически длительный режим graceful degradation: {degradation_duration:.0f} секунд")
                        
        except Exception as e:
            logger.error(f"Ошибка проверки graceful degradation: {e}")
    
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
            # Системная информация - используем неблокирующий вызов
            cpu_percent = psutil.cpu_percent(interval=None)  # Возвращает последнее измеренное значение
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Информация о graceful degradation
            graceful_status = {}
            try:
                from utils.graceful_degradation import graceful_manager
                graceful_status = graceful_manager.get_degradation_status()
            except Exception as e:
                logger.error(f"Ошибка получения статуса graceful degradation: {e}")
                graceful_status = {"error": str(e)}
            
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
            
            # Статус базы данных с таймаутом
            db_status = "healthy"
            session = None
            try:
                from db.database import AsyncSessionLocal
                from sqlalchemy import text
                session = AsyncSessionLocal()
                await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=5.0)
            except asyncio.TimeoutError:
                db_status = "timeout: превышен лимит времени подключения"
            except Exception as e:
                db_status = f"error: {str(e)}"
            finally:
                if session:
                    try:
                        await session.close()
                    except Exception as e:
                        logger.error(f"Ошибка при закрытии сессии БД в get_health_status: {e}")
            
            # Определяем общий статус с правильным приоритетом (critical > warning > healthy)
            overall_status = "healthy"
            
            # Сначала проверяем критические условия
            if (cpu_percent > 95 or memory.percent > 95 or 
                disk.percent > 95 or db_status != "healthy" or
                pool_stats.get("utilization_percent", 0) > 95):
                overall_status = "critical"
            # Затем проверяем предупреждения (только если не critical)
            elif (cpu_percent > 80 or memory.percent > 85 or 
                  disk.percent > 90 or db_status != "healthy" or
                  pool_stats.get("utilization_percent", 0) > 90):
                overall_status = "warning"
            
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
                "pool_stats": pool_stats,
                "graceful_degradation": graceful_status
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
