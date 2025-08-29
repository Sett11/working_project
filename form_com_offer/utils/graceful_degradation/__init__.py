"""
Пакет Graceful Degradation для элегантного снижения функциональности при проблемах.

Экспортирует основные компоненты для использования в приложении.
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, db_circuit_breaker
from .fallback import FallbackManager, fallback_manager
from .graceful_degradation import (
    GracefulDegradationManager, 
    graceful_manager,
    graceful_fallback,
    cache_result,
    critical_data_save,
    handle_database_error,
    graceful_response
)

__all__ = [
    # Circuit Breaker
    'CircuitBreaker',
    'CircuitBreakerOpenError', 
    'db_circuit_breaker',
    
    # Fallback Manager
    'FallbackManager',
    'fallback_manager',
    
    # Graceful Degradation Manager
    'GracefulDegradationManager',
    'graceful_manager',
    
    # Декораторы
    'graceful_fallback',
    'cache_result', 
    'critical_data_save',
    'handle_database_error',
    'graceful_response'
]
