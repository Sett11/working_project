"""
Модуль Graceful Degradation для элегантного снижения функциональности при проблемах.

Обеспечивает:
1. Декораторы для автоматического fallback
2. Обработку ошибок БД
3. Кэширование результатов
4. Graceful responses для API
"""
import functools
import asyncio
import time
from typing import Callable, Any, Optional, Dict
from utils.mylogger import Logger
from .circuit_breaker import db_circuit_breaker, CircuitBreakerOpenError
from .fallback import fallback_manager

logger = Logger("graceful_degradation", "graceful_degradation.log")

def graceful_fallback(endpoint_name: str, cache_key: Optional[str] = None, cache_ttl: int = 300):
    """
    Декоратор для graceful fallback при ошибках БД.
    
    Args:
        endpoint_name: Название эндпоинта для fallback response
        cache_key: Ключ для кэширования результата
        cache_ttl: Время жизни кэша в секундах
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Проверяем Circuit Breaker
                if db_circuit_breaker.get_status()["state"] == "open":
                    logger.warning(f"Circuit Breaker открыт для {endpoint_name}")
                    return fallback_manager.get_graceful_response(endpoint_name)
                
                # Выполняем основную функцию
                result = await func(*args, **kwargs)
                
                # Кэшируем успешный результат
                if cache_key and result:
                    fallback_manager.set_cached_data(cache_key, result, cache_ttl)
                
                return result
                
            except CircuitBreakerOpenError:
                logger.warning(f"Circuit Breaker заблокировал {endpoint_name}")
                return fallback_manager.get_graceful_response(endpoint_name)
                
            except Exception as e:
                logger.error(f"Ошибка в {endpoint_name}: {e}")
                
                # Пытаемся вернуть кэшированные данные
                if cache_key:
                    cached_data = fallback_manager.get_cached_data(cache_key)
                    if cached_data:
                        logger.info(f"Возвращаем кэшированные данные для {endpoint_name}")
                        return fallback_manager.get_graceful_response(
                            endpoint_name, cached_data
                        )
                
                # Возвращаем fallback response
                return fallback_manager.get_graceful_response(endpoint_name)
        
        return wrapper
    return decorator

def cache_result(cache_key: str, ttl_seconds: int = 300):
    """
    Декоратор для кэширования результатов функций.
    
    Args:
        cache_key: Ключ для кэширования
        ttl_seconds: Время жизни кэша
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Проверяем кэш
            cached_result = fallback_manager.get_cached_data(cache_key)
            if cached_result is not None:
                logger.info(f"Возвращаем кэшированный результат для {cache_key}")
                return cached_result
            
            # Выполняем функцию
            result = await func(*args, **kwargs)
            
            # Кэшируем результат
            if result is not None:
                fallback_manager.set_cached_data(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator

def critical_data_save(data_key: str):
    """
    Декоратор для сохранения критических данных.
    
    Args:
        data_key: Ключ для сохранения данных
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Сохраняем критически важные данные
            if result is not None:
                fallback_manager.save_critical_data(data_key, result)
            
            return result
        
        return wrapper
    return decorator

class GracefulDegradationManager:
    """
    Менеджер для управления graceful degradation.
    """
    
    def __init__(self):
        self._degradation_mode = False
        self._degradation_start_time = None
        self._recovery_attempts = 0
        self._max_recovery_attempts = 5
        
        logger.info("Graceful Degradation Manager инициализирован")
    
    def enter_degradation_mode(self, reason: str = "Unknown"):
        """Вход в режим graceful degradation"""
        self._degradation_mode = True
        self._degradation_start_time = time.time()
        logger.warning(f"🚨 Вход в режим graceful degradation: {reason}")
    
    def exit_degradation_mode(self):
        """Выход из режима graceful degradation"""
        if self._degradation_mode:
            duration = time.time() - self._degradation_start_time
            self._degradation_mode = False
            self._degradation_start_time = None
            self._recovery_attempts = 0
            logger.info(f"✅ Выход из режима graceful degradation (длительность: {duration:.1f}s)")
    
    def is_in_degradation_mode(self) -> bool:
        """Проверка, находимся ли в режиме degradation"""
        return self._degradation_mode
    
    def get_degradation_status(self) -> Dict[str, Any]:
        """Получение статуса graceful degradation"""
        return {
            "degradation_mode": self._degradation_mode,
            "degradation_start_time": self._degradation_start_time,
            "degradation_duration": time.time() - self._degradation_start_time if self._degradation_start_time else 0,
            "recovery_attempts": self._recovery_attempts,
            "max_recovery_attempts": self._max_recovery_attempts,
            "circuit_breaker_status": db_circuit_breaker.get_status(),
            "fallback_manager_status": fallback_manager.get_status()
        }
    
    async def attempt_recovery(self) -> bool:
        """Попытка восстановления из режима degradation"""
        if not self._degradation_mode:
            return True
        
        if self._recovery_attempts >= self._max_recovery_attempts:
            logger.warning("Достигнуто максимальное количество попыток восстановления")
            return False
        
        self._recovery_attempts += 1
        logger.info(f"Попытка восстановления #{self._recovery_attempts}")
        
        try:
            # Проверяем состояние Circuit Breaker
            cb_status = db_circuit_breaker.get_status()
            if cb_status["state"] == "closed":
                self.exit_degradation_mode()
                return True
            
            # Если Circuit Breaker в HALF_OPEN, даем ему шанс
            if cb_status["state"] == "half_open":
                logger.info("Circuit Breaker в HALF_OPEN состоянии - ожидаем...")
                await asyncio.sleep(10)  # Даем время для тестовых запросов
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при попытке восстановления: {e}")
            return False

# Глобальный экземпляр менеджера
graceful_manager = GracefulDegradationManager()

def handle_database_error(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок базы данных с graceful degradation.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except CircuitBreakerOpenError:
            graceful_manager.enter_degradation_mode("Circuit Breaker открыт")
            raise
        except Exception as e:
            if "database" in str(e).lower() or "connection" in str(e).lower():
                graceful_manager.enter_degradation_mode(f"Ошибка БД: {e}")
            raise
    return wrapper

def graceful_response(endpoint_name: str):
    """
    Декоратор для создания graceful response при ошибках.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в {endpoint_name}: {e}")
                return fallback_manager.get_graceful_response(endpoint_name)
        return wrapper
    return decorator
