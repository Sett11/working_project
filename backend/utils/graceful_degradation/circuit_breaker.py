"""
Модуль Circuit Breaker для graceful degradation при проблемах с БД.

Circuit Breaker автоматически останавливает попытки подключения к БД
при критических ошибках, предотвращая каскадные сбои.
"""
import asyncio
import time
import os
import threading
from enum import Enum
from typing import Optional, Callable, Any
from utils.mylogger import Logger

logger = Logger("circuit_breaker", "circuit_breaker.log")

class CircuitState(Enum):
    """Состояния Circuit Breaker"""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Блокировка запросов
    HALF_OPEN = "half_open"  # Тестовые запросы

class CircuitBreakerOpenError(Exception):
    """Исключение, возникающее когда Circuit Breaker открыт"""
    pass

class CircuitBreaker:
    """
    Circuit Breaker для защиты от каскадных сбоев БД.
    
    Принцип работы:
    1. CLOSED: Нормальная работа, все запросы проходят
    2. OPEN: При критических ошибках блокирует все запросы
    3. HALF_OPEN: Периодически проверяет восстановление БД
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,        # Количество ошибок для открытия
        recovery_timeout: int = 300,       # Время ожидания (5 минут)
        expected_exception: type = Exception,  # Тип исключения для отслеживания
        monitor_interval: int = 300        # Интервал мониторинга (5 минут - увеличено с 1 минуты для снижения нагрузки на CPU)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.monitor_interval = monitor_interval
        
        # Состояние
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        # Мониторинг
        self._monitor_task = None
        self._monitoring_active = False
        self._state_lock = None  # Ленивая инициализация Lock (создаётся при первом обращении)
        
        logger.info(f"Circuit Breaker инициализирован: threshold={failure_threshold}, "
                   f"timeout={recovery_timeout}s, monitor_interval={monitor_interval}s")
    
    @property
    def state_lock(self):
        """
        Ленивое создание asyncio.Lock при первом обращении.
        Это предотвращает RuntimeError при импорте модуля (когда ещё нет running event loop).
        """
        if self._state_lock is None:
            try:
                self._state_lock = asyncio.Lock()
            except RuntimeError:
                # Нет running event loop - Lock будет создан позже
                logger.debug("Не удалось создать asyncio.Lock (нет running loop), отложена инициализация")
                return None
        return self._state_lock
    
    def _safe_schedule_coroutine(self, coro):
        """
        Безопасное планирование корутины из синхронного контекста.
        
        Args:
            coro: Корутина для выполнения
        """
        try:
            # Пытаемся получить текущий running event loop
            loop = asyncio.get_running_loop()
            # Если loop запущен, планируем задачу безопасно
            loop.call_soon_threadsafe(asyncio.create_task, coro)
            logger.debug("Корутина запланирована через call_soon_threadsafe")
        except RuntimeError:
            # Нет running event loop, запускаем в новом потоке
            def run_in_thread():
                try:
                    asyncio.run(coro)
                except Exception as e:
                    logger.error(f"Ошибка при выполнении корутины в потоке: {e}")
            
            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()
            logger.debug("Корутина запущена в отдельном потоке (нет running event loop)")
    
    async def start_monitoring(self):
        """Запуск автоматического мониторинга состояния"""
        if self._monitoring_active:
            return
            
        self._monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Мониторинг Circuit Breaker запущен")
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        self._monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Мониторинг Circuit Breaker остановлен")
    
    async def _monitor_loop(self):
        """Основной цикл мониторинга (оптимизирован для снижения нагрузки на CPU)"""
        while self._monitoring_active:
            try:
                await self._check_state_transition()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга Circuit Breaker: {e}")
                await asyncio.sleep(60)  # Увеличено с 10 до 60 секунд для снижения нагрузки
    
    async def _check_state_transition(self):
        """Проверка необходимости смены состояния"""
        current_time = time.time()
        
        if self.state == CircuitState.OPEN:
            # Проверяем, не пора ли перейти в HALF_OPEN
            if (self.last_failure_time and 
                current_time - self.last_failure_time >= self.recovery_timeout):
                # Защита от state_lock = None
                if self.state_lock is None:
                    # Если нет блокировки, выполняем проверку напрямую
                    if (self.state == CircuitState.OPEN and self.last_failure_time and 
                        current_time - self.last_failure_time >= self.recovery_timeout):
                        await self._transition_to_half_open()
                else:
                    async with self.state_lock:
                        # Повторная проверка под блокировкой (double-checked locking)
                        if (self.state == CircuitState.OPEN and self.last_failure_time and 
                            current_time - self.last_failure_time >= self.recovery_timeout):
                            await self._transition_to_half_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            # В HALF_OPEN состоянии не делаем автоматических переходов
            # Переход происходит только при успешных/неуспешных запросах
            pass
    
    async def _transition_to_half_open(self):
        """
        Переход в состояние HALF_OPEN.
        ВАЖНО: Вызывающая сторона должна держать self.state_lock!
        """
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
        logger.warning("🔄 Circuit Breaker перешел в состояние HALF_OPEN - "
                      "разрешаем тестовые запросы к БД")
    
    async def _transition_to_open(self):
        """
        Переход в состояние OPEN (блокировка).
        ВАЖНО: Вызывающая сторона должна держать self.state_lock!
        """
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        logger.error(f"🚨 Circuit Breaker ОТКРЫТ - блокируем запросы к БД "
                    f"на {self.recovery_timeout} секунд")
    
    async def _transition_to_closed(self):
        """
        Переход в состояние CLOSED (нормальная работа).
        ВАЖНО: Вызывающая сторона должна держать self.state_lock!
        """
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_success_time = time.time()
        logger.info("✅ Circuit Breaker ЗАКРЫТ - нормальная работа БД восстановлена")
    
    def _on_success(self):
        """Обработка успешного запроса (синхронная версия для call())"""
        if self.state == CircuitState.HALF_OPEN:
            # В HALF_OPEN успех означает восстановление БД
            self._safe_schedule_coroutine(self._safe_transition_to_closed())
        else:
            # В CLOSED просто сбрасываем счетчик ошибок
            self.failure_count = 0
            self.last_success_time = time.time()
    
    async def _a_on_success(self):
        """Обработка успешного запроса (асинхронная версия для acall())"""
        if self.state == CircuitState.HALF_OPEN:
            # В HALF_OPEN успех означает восстановление БД - ждем завершения перехода
            await self._safe_transition_to_closed()
        else:
            # В CLOSED просто сбрасываем счетчик ошибок
            self.failure_count = 0
            self.last_success_time = time.time()

    async def _safe_transition_to_closed(self):
        """Thread-safe переход в CLOSED состояние из HALF_OPEN"""
        # Защита от state_lock = None
        if self.state_lock is None:
            # Если нет блокировки, выполняем переход напрямую
            if self.state == CircuitState.HALF_OPEN:
                await self._transition_to_closed()
        else:
            async with self.state_lock:
                # Проверка состояния под блокировкой, затем прямой вызов _transition_to_closed
                # (блокировка уже захвачена, поэтому вложенного захвата не будет)
                if self.state == CircuitState.HALF_OPEN:
                    await self._transition_to_closed()
    
    async def _safe_transition_to_open(self):
        """Thread-safe переход в OPEN состояние"""
        # Валидация состояния: проверяем, что состояние существует и не OPEN
        if self.state is None:
            logger.warning("Попытка перехода в OPEN при state=None, пропускаем")
            return
        
        if self.state == CircuitState.OPEN:
            logger.debug("Circuit Breaker уже в состоянии OPEN, пропускаем повторный переход")
            return
        
        # Защита от state_lock = None
        if self.state_lock is None:
            # Если нет блокировки, выполняем переход напрямую
            logger.debug("state_lock=None, выполняем переход в OPEN без блокировки")
            await self._transition_to_open()
        else:
            async with self.state_lock:
                # Повторная проверка под блокировкой (double-checked locking)
                if self.state != CircuitState.OPEN:
                    await self._transition_to_open()
    
    def _on_failure(self, error: Exception):
        """Обработка неуспешного запроса (синхронная версия для call())"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(f"Ошибка БД #{self.failure_count}: {error}")
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                # Планируем переход в фоне (неблокирующий)
                self._safe_schedule_coroutine(self._safe_transition_to_open())
        
        elif self.state == CircuitState.HALF_OPEN:
            # В HALF_OPEN любая ошибка возвращает в OPEN (планируем в фоне)
            self._safe_schedule_coroutine(self._safe_transition_to_open())
    
    async def _a_on_failure(self, error: Exception):
        """Обработка неуспешного запроса (асинхронная версия для acall())"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(f"Ошибка БД #{self.failure_count}: {error}")
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                # Ждем завершения перехода в OPEN перед возвратом
                await self._safe_transition_to_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            # В HALF_OPEN любая ошибка возвращает в OPEN - ждем завершения перехода
            await self._safe_transition_to_open()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Выполняет функцию с защитой Circuit Breaker.
        
        Args:
            func: Функция для выполнения
            *args, **kwargs: Аргументы функции
            
        Returns:
            Результат выполнения функции
            
        Raises:
            CircuitBreakerOpenError: Если Circuit Breaker открыт
            Exception: Оригинальная ошибка функции
        """
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit Breaker открыт. Последняя ошибка: {self.last_failure_time}"
            )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise
    
    async def acall(self, func: Callable, *args, **kwargs) -> Any:
        """
        Асинхронная версия call().
        """
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit Breaker открыт. Последняя ошибка: {self.last_failure_time}"
            )
        
        try:
            result = await func(*args, **kwargs)
            # Используем асинхронную версию для ожидания завершения переходов
            await self._a_on_success()
            return result
        except self.expected_exception as e:
            # Используем асинхронную версию для ожидания завершения переходов
            await self._a_on_failure(e)
            raise
    
    def get_status(self) -> dict:
        """Получение статуса Circuit Breaker"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "recovery_timeout": self.recovery_timeout,
            "monitoring_active": self._monitoring_active
        }

def _safe_int(env_name: str, default: int) -> int:
    """
    Безопасное преобразование переменной окружения в int.
    
    Args:
        env_name: Имя переменной окружения
        default: Значение по умолчанию
        
    Returns:
        Целое число из переменной окружения или default при ошибке
    """
    try:
        value = os.getenv(env_name)
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Не удалось преобразовать {env_name}='{os.getenv(env_name)}' в int: {e}. "
                      f"Используется значение по умолчанию: {default}")
        return default

# Глобальный экземпляр Circuit Breaker для БД
db_circuit_breaker = CircuitBreaker(
    failure_threshold=_safe_int("CB_FAILURE_THRESHOLD", 3),
    recovery_timeout=_safe_int("CB_RECOVERY_TIMEOUT", 300),
    expected_exception=(Exception,),  # Все исключения
    monitor_interval=_safe_int("CB_MONITOR_INTERVAL", 300)  # 300 секунд (5 минут)
)