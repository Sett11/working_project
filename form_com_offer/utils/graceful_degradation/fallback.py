"""
Модуль Fallback механизмов для graceful degradation.

Обеспечивает альтернативные способы работы при недоступности БД.
"""
import json
import time
import os
import asyncio
from typing import Dict, Any, List, Optional
from utils.mylogger import Logger

logger = Logger("fallback", "fallback.log")

class FallbackManager:
    """
    Менеджер fallback механизмов для graceful degradation.
    
    Обеспечивает:
    1. Кэширование данных в памяти
    2. Возврат заглушек при недоступности БД
    3. Локальное хранение критических данных
    4. Graceful degradation для API эндпоинтов
    """
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 600  # 10 минут TTL для кэша (увеличено с 5 минут для снижения нагрузки)
        self._fallback_data = {}
        self._last_db_access = None
        self._fallback_storage_path = "logs/fallback_storage.json"
        self._cleanup_task = None
        self._is_running = False
        self._loop = None  # Сохраняем текущий event loop
        
        # Инициализируем fallback данные
        self._init_fallback_data()
        
        logger.info("Fallback Manager инициализирован (планировщик не запущен)")
    
    def _init_fallback_data(self):
        """Инициализация базовых fallback данных"""
        # Заглушки для основных эндпоинтов
        self._fallback_data["orders_list"] = {
            "data": [],
            "message": "База данных временно недоступна. Данные могут быть устаревшими.",
            "timestamp": time.time(),
            "ttl": 1200  # 20 минут (увеличено с 10 минут)
        }
        
        self._fallback_data["health_status"] = {
            "data": {
                "status": "degraded",
                "message": "Приложение работает в режиме graceful degradation",
                "database": "unavailable",
                "fallback_mode": True
            },
            "timestamp": time.time(),
            "ttl": 600  # Увеличено с 300 до 600 секунд (10 минут)
        }
        
        self._fallback_data["monitoring_status"] = {
            "data": {
                "timestamp": time.time(),
                "overall_status": "degraded",
                "system": {
                    "cpu_percent": 0,
                    "memory_percent": 0,
                    "memory_available_mb": 0,
                    "disk_usage_percent": 0
                },
                "database_status": "unavailable",
                "pool_stats": {"error": "Database unavailable"},
                "graceful_degradation": {
                    "degradation_mode": True,
                    "degradation_start_time": time.time(),
                    "degradation_duration": 0,
                    "recovery_attempts": 0,
                    "max_recovery_attempts": 5
                }
            },
            "timestamp": time.time(),
            "ttl": 300  # Увеличено с 60 до 300 секунд (5 минут)
        }
        
        logger.info("Fallback данные инициализированы")
    
    def start(self):
        """Запуск планировщика автоматической очистки"""
        if self._is_running:
            logger.warning("Fallback Manager уже запущен")
            return
        
        try:
            # Получаем и сохраняем активный event loop
            self._loop = asyncio.get_running_loop()
            # Создаем задачу на сохраненном loop
            self._cleanup_task = self._loop.create_task(self._cleanup_loop())
            self._is_running = True
            logger.info("✅ Планировщик автоматической очистки запущен")
            
        except RuntimeError as e:
            logger.warning(f"Event loop не запущен, планировщик не запущен: {e}")
            # Убеждаемся, что _cleanup_task и _loop остаются None
            self._cleanup_task = None
            self._loop = None
            self._is_running = False
        except Exception as e:
            import traceback
            logger.error(f"Ошибка запуска планировщика: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Убеждаемся, что _cleanup_task и _loop остаются None при ошибке
            self._cleanup_task = None
            self._loop = None
            self._is_running = False
    
    def stop(self):
        """Остановка планировщика автоматической очистки (синхронный вариант)"""
        if not self._is_running:
            logger.info("Fallback Manager уже остановлен")
            return
        
        try:
            if self._cleanup_task and not self._cleanup_task.done():
                if self._loop and self._loop.is_running():
                    # Thread-safe отмена задачи на сохраненном loop
                    self._loop.call_soon_threadsafe(self._cleanup_task.cancel)
                    logger.info("✅ Задача автоматической очистки отменена (thread-safe)")
                else:
                    # Fallback отмена
                    self._cleanup_task.cancel()
                    logger.info("✅ Задача автоматической очистки отменена (fallback)")
            
            self._is_running = False
            self._cleanup_task = None
            self._loop = None
            
            # Выполняем финальную очистку
            self.cleanup_expired_data()
            logger.info("✅ Fallback Manager остановлен")
            
        except Exception as e:
            logger.error(f"Ошибка при остановке Fallback Manager: {e}")
    
    async def stop_async(self):
        """Остановка планировщика автоматической очистки (асинхронный вариант)"""
        if not self._is_running:
            logger.info("Fallback Manager уже остановлен")
            return
        
        try:
            if self._cleanup_task and not self._cleanup_task.done():
                # Отменяем задачу на сохраненном loop
                if self._loop and self._loop.is_running():
                    self._loop.call_soon_threadsafe(self._cleanup_task.cancel)
                else:
                    self._cleanup_task.cancel()
                
                logger.info("✅ Задача автоматической очистки отменена")
                
                # Ожидаем завершения задачи с ограничением времени
                try:
                    await asyncio.wait_for(self._cleanup_task, timeout=5.0)
                    logger.info("✅ Задача автоматической очистки успешно завершена")
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Таймаут ожидания завершения задачи очистки (5 сек)")
                except asyncio.CancelledError:
                    logger.info("✅ Задача автоматической очистки корректно отменена")
                except Exception as e:
                    logger.error(f"Ошибка при ожидании завершения задачи очистки: {e}")
            
            self._is_running = False
            self._cleanup_task = None
            self._loop = None
            
            # Выполняем финальную очистку
            self.cleanup_expired_data()
            logger.info("✅ Fallback Manager остановлен")
            
        except Exception as e:
            import traceback
            logger.error(f"Ошибка при остановке Fallback Manager: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Убеждаемся, что состояние корректно сброшено
            self._is_running = False
            self._cleanup_task = None
            self._loop = None
    
    def set_cache_ttl(self, ttl_seconds: int):
        """Установка времени жизни кэша"""
        self._cache_ttl = ttl_seconds
        logger.info(f"TTL кэша установлен: {ttl_seconds} секунд")
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Получение данных из кэша"""
        if key not in self._cache:
            return None
        
        cached_item = self._cache[key]
        if time.time() - cached_item["timestamp"] > self._cache_ttl:
            # Кэш устарел
            del self._cache[key]
            return None
        
        logger.info(f"Получены данные из кэша: {key}")
        return cached_item["data"]
    
    def set_cached_data(self, key: str, data: Any, ttl_seconds: Optional[int] = None):
        """Сохранение данных в кэш"""
        ttl = ttl_seconds or self._cache_ttl
        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
            "ttl": ttl
        }
        logger.info(f"Данные сохранены в кэш: {key} (TTL: {ttl}s)")
    
    def set_fallback_data(self, key: str, data: Any, ttl_seconds: int = 300):
        """Установка заглушки в кэш"""
        self._fallback_data[key] = {
            "data": data,
            "timestamp": time.time(),
            "ttl": ttl_seconds
        }
        logger.info(f"Заглушка установлена в кэш: {key}")

    def get_fallback_data(self, key: str) -> Optional[Any]:
        """Получение заглушки из кэша"""
        if key not in self._fallback_data:
            return None
        
        fallback_item = self._fallback_data[key]
        if time.time() - fallback_item["timestamp"] > fallback_item["ttl"]:
            # Заглушка устарела
            del self._fallback_data[key]
            return None
        
        logger.info(f"Получена заглушка: {key}")
        return fallback_item["data"]
    
    def save_critical_data(self, key: str, data: Any):
        """Сохранение критических данных в файл"""
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self._fallback_storage_path), exist_ok=True)
            
            # Загружаем существующие данные
            existing_data = {}
            if os.path.exists(self._fallback_storage_path):
                try:
                    with open(self._fallback_storage_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Ошибка чтения fallback storage: {e}")
            
            # Добавляем новые данные
            existing_data[key] = {
                "data": data,
                "timestamp": time.time()
            }
            
            # Сохраняем обратно
            with open(self._fallback_storage_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Критические данные сохранены: {key}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения критических данных: {e}")
    
    def load_critical_data(self, key: str) -> Optional[Any]:
        """Загрузка критических данных из файла"""
        try:
            if not os.path.exists(self._fallback_storage_path):
                return None
            
            with open(self._fallback_storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if key in data:
                logger.info(f"Критические данные загружены: {key}")
                return data[key]["data"]
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки критических данных: {e}")
            return None
    
    def get_graceful_response(self, endpoint: str, original_data: Any = None) -> Dict[str, Any]:
        """Создание graceful response для API эндпоинтов"""
        
        # Базовые graceful responses
        graceful_responses = {
            "orders_list": {
                "success": True,
                "data": self.get_cached_data("orders_list") or [],
                "message": "Данные могут быть устаревшими. База данных временно недоступна.",
                "fallback_mode": True,
                "cached_at": time.time()
            },
            "health_check": {
                "status": "degraded",
                "database": "unavailable",
                "message": "Приложение работает в режиме graceful degradation",
                "fallback_mode": True,
                "timestamp": time.time()
            },
            "monitoring_status": {
                "overall_status": "degraded",
                "database_status": "unavailable",
                "fallback_mode": True,
                "message": "Мониторинг работает в fallback режиме",
                "timestamp": time.time()
            }
        }
        
        # Если есть оригинальные данные, пытаемся их использовать
        if original_data and endpoint in graceful_responses:
            graceful_responses[endpoint]["data"] = original_data
            graceful_responses[endpoint]["original_data"] = True
        
        # Возвращаем graceful response или базовый fallback
        return graceful_responses.get(endpoint, {
            "success": False,
            "message": "Сервис временно недоступен. Попробуйте позже.",
            "fallback_mode": True,
            "timestamp": time.time()
        })
    
    def cleanup_expired_data(self):
        """Очистка устаревших данных"""
        current_time = time.time()
        
        # Очистка кэша - безопасная итерация по копии
        expired_cache_keys = [
            key for key, item in list(self._cache.items())
            if current_time - item["timestamp"] > item["ttl"]
        ]
        for key in expired_cache_keys:
            del self._cache[key]
        
        # Очистка fallback данных - безопасная итерация по копии
        expired_fallback_keys = [
            key for key, item in list(self._fallback_data.items())
            if current_time - item["timestamp"] > item["ttl"]
        ]
        for key in expired_fallback_keys:
            del self._fallback_data[key]
        
        if expired_cache_keys or expired_fallback_keys:
            logger.info(f"Очищено устаревших данных: кэш={len(expired_cache_keys)}, "
                       f"fallback={len(expired_fallback_keys)}")
    
    def _start_cleanup_scheduler(self):
        """Запуск планировщика автоматической очистки (устаревший метод)"""
        logger.warning("_start_cleanup_scheduler устарел, используйте start()")
        self.start()
    
    async def _cleanup_loop(self):
        """Асинхронный цикл автоматической очистки (оптимизирован для снижения нагрузки на CPU)"""
        while self._is_running:
            try:
                await asyncio.sleep(900)  # Очистка каждые 15 минут (увеличено с 5 минут для снижения нагрузки)
                if self._is_running:  # Дополнительная проверка
                    self.cleanup_expired_data()
            except asyncio.CancelledError:
                logger.info("Цикл автоматической очистки остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле автоматической очистки: {e}")
                if self._is_running:  # Дополнительная проверка
                    await asyncio.sleep(300)  # Пауза при ошибке увеличена до 5 минут
    
    def close(self):
        """Корректное завершение работы Fallback Manager (устаревший метод)"""
        logger.warning("close() устарел, используйте stop()")
        self.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса Fallback Manager"""
        cleanup_task_status = "running" if (self._cleanup_task and not self._cleanup_task.done()) else "stopped"
        loop_status = "available" if (self._loop and self._loop.is_running()) else "unavailable"
        
        return {
            "cache_size": len(self._cache),
            "fallback_data_size": len(self._fallback_data),
            "cache_ttl": self._cache_ttl,
            "last_db_access": self._last_db_access,
            "fallback_storage_path": self._fallback_storage_path,
            "fallback_storage_exists": os.path.exists(self._fallback_storage_path),
            "cleanup_task_status": cleanup_task_status,
            "loop_status": loop_status,
            "is_running": self._is_running
        }

# Глобальный экземпляр Fallback Manager (без автоматического запуска)
fallback_manager = FallbackManager()