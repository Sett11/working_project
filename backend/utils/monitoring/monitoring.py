"""
Модуль автоматического мониторинга состояния приложения
"""
import asyncio
import time
import re
import psutil
from typing import Dict, Any, Optional
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
                await asyncio.sleep(600)  # Проверяем каждые 10 минут (увеличено с 5 минут)
                
            except asyncio.CancelledError:
                raise  # Re-raise CancelledError to allow proper task cancellation
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # При ошибке проверяем через 1 минуту (увеличено с 30 секунд)
    
    async def _check_system_health(self):
        """Проверка системного здоровья (оптимизировано для контейнеров)"""
        try:
            # В контейнерах Docker psutil.cpu_percent(interval=None) может работать некорректно
            # Используем более безопасный подход с минимальным интервалом
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Минимальный интервал для корректной работы
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Проверяем критические пороги
            if cpu_percent > 80:
                await self._send_alert("system", f"Высокая загрузка CPU: {cpu_percent}%", 
                                      alert_template="high_cpu")
            
            if memory.percent > 85:
                await self._send_alert("system", f"Высокое потребление памяти: {memory.percent}%", 
                                      alert_template="high_memory")
            
            if disk.percent > 90:
                await self._send_alert("system", f"Критическое заполнение диска: {disk.percent}%", 
                                      alert_template="high_disk")
                
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
            await self._send_alert("database", "Таймаут подключения к БД (5 секунд)", 
                                  alert_template="db_timeout")
        except Exception as e:
            await self._send_alert("database", f"Ошибка подключения к БД: {e}", 
                                  alert_template="db_connection_error")
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
                await self._send_alert("pool", f"Высокая утилизация пула: {utilization:.1f}%", 
                                      alert_template="high_pool_utilization")
            
            if overflow > 5:
                await self._send_alert("pool", f"Переполнение пула: {overflow} соединений", 
                                      alert_template="pool_overflow")
            
            if checked_out == pool_size:
                await self._send_alert("pool", "Все соединения в пуле заняты!", 
                                      alert_template="pool_exhausted")
                
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
                        f"Длительный режим graceful degradation: {degradation_duration:.0f} секунд",
                        alert_template="long_degradation")
                
                # Алерт если исчерпаны попытки восстановления
                if recovery_attempts >= max_attempts:
                    await self._send_alert("graceful_degradation", 
                        f"Исчерпаны попытки восстановления: {recovery_attempts}/{max_attempts}",
                        alert_template="recovery_exhausted")
                
                # Алерт если degradation длится более 30 минут
                if degradation_duration > 1800:  # 30 минут
                    await self._send_alert("graceful_degradation", 
                        f"Критически длительный режим graceful degradation: {degradation_duration:.0f} секунд",
                        alert_template="critical_degradation")
                        
        except Exception as e:
            logger.error(f"Ошибка проверки graceful degradation: {e}")
    
    def _normalize_alert_key(self, message: str) -> str:
        """
        Нормализация сообщения алерта для создания статического ключа.
        Удаляет динамические части: числа, проценты, временные метки.
        
        Примеры:
        - "Высокая загрузка CPU: 85.3%" -> "Высокая загрузка CPU: %"
        - "Переполнение пула: 7 соединений" -> "Переполнение пула: соединений"
        - "Длительный режим graceful degradation: 650 секунд" -> "Длительный режим graceful degradation: секунд"
        """
        # Удаляем числа (целые и дробные) и проценты
        normalized = re.sub(r'\d+\.?\d*%?', '', message)
        # Удаляем множественные пробелы
        normalized = re.sub(r'\s+', ' ', normalized)
        # Убираем лишние пробелы в начале/конце
        normalized = normalized.strip()
        return normalized
    
    async def _send_alert(self, alert_type: str, message: str, alert_template: Optional[str] = None):
        """
        Отправка алерта с защитой от спама.
        
        Args:
            alert_type: Тип алерта (system, database, pool, graceful_degradation)
            message: Полное динамическое сообщение для логирования
            alert_template: Опциональный статический шаблон для ключа cooldown.
                          Если не указан, будет создан автоматически путем нормализации message.
        """
        current_time = time.time()
        
        # Используем явный шаблон или нормализуем сообщение для создания статического ключа
        template = alert_template if alert_template else self._normalize_alert_key(message)
        alert_key = f"{alert_type}_{template}"
        
        # Проверяем, не отправляли ли мы недавно такой же алерт
        if alert_key in self.last_alert_time:
            if current_time - self.last_alert_time[alert_key] < self.alert_cooldown:
                # Логируем факт пропуска алерта (debug level)
                logger.debug(f"Алерт пропущен (cooldown): [{alert_type.upper()}] {message}")
                return
        
        # Логируем алерт с полным динамическим сообщением
        logger.warning(f"🚨 АЛЕРТ [{alert_type.upper()}]: {message}")
        self.last_alert_time[alert_key] = current_time
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Получение текущего статуса здоровья приложения"""
        try:
            # Системная информация - оптимизировано для контейнеров
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Минимальный интервал для корректной работы в контейнерах
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
            
            # Дополнительные системные метрики
            cpu_count = psutil.cpu_count()
            disk_free_gb = round(disk.free / 1024 / 1024 / 1024, 2)
            
            # Сетевая активность
            network_connections = len(psutil.net_connections())
            # Более реалистичная нормализация сетевой активности
            # 0-50 соединений = 0-50%, 50-200 = 50-80%, 200+ = 80-100%
            if network_connections <= 50:
                network_usage_percent = network_connections * 1.0  # 0-50%
            elif network_connections <= 200:
                network_usage_percent = 50 + (network_connections - 50) * 0.2  # 50-80%
            else:
                network_usage_percent = min(80 + (network_connections - 200) * 0.1, 100)  # 80-100%
            
            # Температура CPU (если доступна)
            cpu_temperature = 0
            cpu_temperature_max = 0
            try:
                if hasattr(psutil, 'sensors_temperatures'):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            for entry in entries:
                                if 'cpu' in name.lower() or 'core' in name.lower():
                                    cpu_temperature = max(cpu_temperature, entry.current or 0)
                                    cpu_temperature_max = max(cpu_temperature_max, entry.high or 0)
                
                # Если температура не получена, используем эмуляцию на основе загрузки CPU
                if cpu_temperature == 0:
                    # Эмуляция: базовая температура 30°C + загрузка CPU * 0.5
                    cpu_temperature = 30 + cpu_percent * 0.5
                    cpu_temperature_max = 80  # Максимальная температура
                    
            except Exception as e:
                logger.debug(f"Не удалось получить температуру CPU: {e}")
                # Fallback: эмуляция на основе загрузки CPU
                cpu_temperature = 30 + cpu_percent * 0.5
                cpu_temperature_max = 80
            
            # Время работы системы
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600
            uptime_days = uptime_hours / 24
            
            return {
                "timestamp": time.time(),
                "overall_status": overall_status,
                "system": {
                    "cpu_percent": cpu_percent,
                    "cpu_count": cpu_count,
                    "memory_percent": memory.percent,
                    "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                    "disk_usage_percent": disk.percent,
                    "disk_free_gb": disk_free_gb,
                    "network_usage_percent": network_usage_percent,
                    "network_connections": network_connections,
                    "cpu_temperature": cpu_temperature,
                    "cpu_temperature_max": cpu_temperature_max,
                    "uptime_hours": uptime_hours,
                    "uptime_days": uptime_days
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
