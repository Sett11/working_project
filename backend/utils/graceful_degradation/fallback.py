"""
Модуль Fallback механизмов для graceful degradation.

Обеспечивает альтернативные способы работы при недоступности БД.
"""
import json
import time
import os
import asyncio
import threading
import tempfile
from collections import OrderedDict
from typing import Dict, Any, List, Optional
from utils.mylogger import Logger

# Импорт portalocker для кросс-платформенной файловой блокировки
try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False

# Импорт fcntl для Unix-систем (fallback блокировка)
HAS_FCNTL = False
if os.name != 'nt':  # Не Windows
    try:
        import fcntl
        HAS_FCNTL = True
    except ImportError:
        HAS_FCNTL = False

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
        # Thread-safe кэш с использованием OrderedDict для O(1) LRU
        self._cache = OrderedDict()
        self._cache_lock = threading.Lock()  # Блокировка для thread-safe операций с кэшем
        self._cache_ttl = 600  # 10 минут TTL для кэша (увеличено с 5 минут для снижения нагрузки)
        self._max_cache_size = 1000  # Максимальное количество элементов в кэше
        
        self._fallback_data = {}
        self._last_db_access = None
        self._fallback_storage_path = "logs/fallback_storage.json"
        self._file_lock_path = "logs/fallback_storage.lock"  # Путь к файлу блокировки
        self._cleanup_task = None
        self._is_running = False
        self._loop = None  # Сохраняем текущий event loop
        
        # Проверка доступности механизма блокировки файлов
        self._check_file_locking_availability()
        
        # Инициализируем fallback данные
        self._init_fallback_data()
        
        if not HAS_PORTALOCKER and HAS_FCNTL:
            logger.warning("⚠️ portalocker не установлен. Используется fcntl для файловой блокировки (только Unix).")
        
        logger.info("Fallback Manager инициализирован (планировщик не запущен)")
    
    def _check_file_locking_availability(self):
        """
        Проверка доступности механизмов файловой блокировки.
        Fail-fast если на Windows нет portalocker.
        """
        if os.name == 'nt':  # Windows
            if not HAS_PORTALOCKER:
                error_msg = (
                    "КРИТИЧЕСКАЯ ОШИБКА: На Windows требуется библиотека portalocker для безопасной "
                    "файловой блокировки. Без неё возможна коррупция данных при конкурентной записи. "
                    "Установите portalocker командой: pip install portalocker"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            logger.info("✓ Используется portalocker для файловой блокировки (Windows)")
        else:  # Unix-like системы
            if HAS_PORTALOCKER:
                logger.info("✓ Используется portalocker для файловой блокировки (кросс-платформенный)")
            elif HAS_FCNTL:
                logger.info("✓ Используется fcntl для файловой блокировки (Unix/Linux)")
            else:
                error_msg = (
                    "КРИТИЧЕСКАЯ ОШИБКА: Не найден ни portalocker, ни fcntl для файловой блокировки. "
                    "Установите portalocker командой: pip install portalocker"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
    
    def _acquire_lock(self, lock_file, lock_type: str = "exclusive"):
        """
        Получение блокировки файла.
        
        Args:
            lock_file: Открытый файловый дескриптор
            lock_type: Тип блокировки ("exclusive" для записи, "shared" для чтения)
        """
        if HAS_PORTALOCKER:
            # Используем portalocker (кросс-платформенный)
            lock_mode = portalocker.LOCK_EX if lock_type == "exclusive" else portalocker.LOCK_SH
            portalocker.lock(lock_file, lock_mode)
            logger.debug(f"Получена {lock_type} блокировка через portalocker: {self._file_lock_path}")
        elif HAS_FCNTL:
            # Используем fcntl на Unix-системах
            lock_mode = fcntl.LOCK_EX if lock_type == "exclusive" else fcntl.LOCK_SH
            fcntl.flock(lock_file, lock_mode)
            logger.debug(f"Получена {lock_type} блокировка через fcntl: {self._file_lock_path}")
        else:
            # Не должны сюда попасть благодаря _check_file_locking_availability
            raise RuntimeError("Механизм файловой блокировки недоступен")
    
    def _release_lock(self, lock_file):
        """
        Освобождение блокировки файла.
        
        Args:
            lock_file: Открытый файловый дескриптор
        """
        try:
            if HAS_PORTALOCKER:
                portalocker.unlock(lock_file)
                logger.debug(f"Блокировка освобождена через portalocker: {self._file_lock_path}")
            elif HAS_FCNTL:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                logger.debug(f"Блокировка освобождена через fcntl: {self._file_lock_path}")
        except Exception as e:
            logger.warning(f"Ошибка при освобождении блокировки: {e}")
    
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
    
    def set_max_cache_size(self, max_size: int):
        """Установка максимального размера кэша (thread-safe)"""
        with self._cache_lock:
            self._max_cache_size = max_size
            logger.info(f"Максимальный размер кэша установлен: {max_size} элементов")
            
            # Если текущий размер превышает новый лимит, удаляем лишние элементы
            items_to_remove = len(self._cache) - max_size
            if items_to_remove > 0:
                # OrderedDict: удаляем самые старые элементы (с начала)
                for _ in range(items_to_remove):
                    self._cache.popitem(last=False)
                
                logger.info(f"Кэш превышал лимит, удалено {items_to_remove} старых элементов")
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Получение данных из кэша (thread-safe с LRU)"""
        with self._cache_lock:
            if key not in self._cache:
                return None
            
            cached_item = self._cache[key]
            # Проверяем TTL для конкретного элемента
            ttl = cached_item.get("ttl", self._cache_ttl)
            if time.time() - cached_item["timestamp"] > ttl:
                # Кэш устарел - удаляем
                del self._cache[key]
                logger.info(f"Кэш устарел и удален: {key}")
                return None
            
            # Обновляем порядок использования (перемещаем в конец = recently used)
            self._cache.move_to_end(key)
            
            logger.info(f"Получены данные из кэша: {key}")
            return cached_item["data"]
    
    def set_cached_data(self, key: str, data: Any, ttl_seconds: Optional[int] = None):
        """Сохранение данных в кэш с ограничением размера (thread-safe с O(1) LRU eviction)"""
        ttl = ttl_seconds or self._cache_ttl
        
        with self._cache_lock:
            # Проверяем размер кэша и удаляем самый старый элемент если нужно
            if len(self._cache) >= self._max_cache_size:
                # O(1) операция: удаляем самый старый элемент (первый в OrderedDict)
                evicted_key, _ = self._cache.popitem(last=False)
                logger.info(f"Кэш переполнен, удален старый элемент: {evicted_key}")
            
            # Добавляем или обновляем элемент
            self._cache[key] = {
                "data": data,
                "timestamp": time.time(),
                "ttl": ttl
            }
            
            # Перемещаем элемент в конец (most recently used)
            self._cache.move_to_end(key)
            
            logger.info(f"Данные сохранены в кэш: {key} (TTL: {ttl}s, размер кэша: {len(self._cache)}/{self._max_cache_size})")
    
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
        """Сохранение критических данных в файл (атомарная операция с файловой блокировкой)"""
        lock_file = None
        temp_file = None
        
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self._fallback_storage_path), exist_ok=True)
            
            # Открываем файл блокировки для exclusive доступа
            lock_file = open(self._file_lock_path, 'w')
            
            try:
                # Получаем эксклюзивную блокировку через unified API
                self._acquire_lock(lock_file, lock_type="exclusive")
                
                # Загружаем существующие данные внутри блокировки
                existing_data = {}
                if os.path.exists(self._fallback_storage_path):
                    try:
                        with open(self._fallback_storage_path, 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)
                    except Exception as e:
                        logger.warning(f"Ошибка чтения fallback storage: {e}, создаем новый файл")
                
                # Добавляем новые данные
                existing_data[key] = {
                    "data": data,
                    "timestamp": time.time()
                }
                
                # Атомарная запись: сначала во временный файл
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=os.path.dirname(self._fallback_storage_path),
                    prefix='.fallback_tmp_',
                    suffix='.json'
                )
                temp_file = temp_path
                
                try:
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                        json.dump(existing_data, f, ensure_ascii=False, indent=2)
                    
                    # Атомарная замена: os.replace гарантирует атомарность на всех платформах
                    os.replace(temp_path, self._fallback_storage_path)
                    temp_file = None  # Успешно перемещен, не нужно удалять
                    
                    logger.info(f"Критические данные атомарно сохранены: {key}")
                    
                except Exception as e:
                    logger.error(f"Ошибка записи во временный файл: {e}")
                    raise
                    
            finally:
                # Освобождаем блокировку через unified API
                self._release_lock(lock_file)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения критических данных: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
        finally:
            # Закрываем файл блокировки
            if lock_file:
                try:
                    lock_file.close()
                except Exception as e:
                    logger.warning(f"Ошибка закрытия файла блокировки: {e}")
            
            # Удаляем временный файл если он остался
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.debug(f"Временный файл удален: {temp_file}")
                except Exception as e:
                    logger.warning(f"Ошибка удаления временного файла {temp_file}: {e}")
    
    def load_critical_data(self, key: str) -> Optional[Any]:
        """Загрузка критических данных из файла (с shared блокировкой для чтения)"""
        lock_file = None
        
        try:
            if not os.path.exists(self._fallback_storage_path):
                return None
            
            # Открываем файл блокировки для shared доступа (чтение)
            lock_file = open(self._file_lock_path, 'w')
            
            try:
                # Получаем shared блокировку через unified API (несколько читателей могут работать одновременно)
                self._acquire_lock(lock_file, lock_type="shared")
                
                # Читаем данные внутри блокировки
                with open(self._fallback_storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if key in data:
                    logger.info(f"Критические данные загружены: {key}")
                    return data[key]["data"]
                
                return None
                
            finally:
                # Освобождаем блокировку через unified API
                self._release_lock(lock_file)
            
        except Exception as e:
            logger.error(f"Ошибка загрузки критических данных: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
            
        finally:
            # Закрываем файл блокировки
            if lock_file:
                try:
                    lock_file.close()
                except Exception as e:
                    logger.warning(f"Ошибка закрытия файла блокировки: {e}")
    
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
        """Очистка устаревших данных (thread-safe)"""
        current_time = time.time()
        
        # Очистка кэша с блокировкой
        with self._cache_lock:
            expired_cache_keys = [
                key for key, item in list(self._cache.items())
                if current_time - item["timestamp"] > item.get("ttl", self._cache_ttl)
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
            "max_cache_size": self._max_cache_size,
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