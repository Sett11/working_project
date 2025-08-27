"""
Экспортер метрик для Prometheus
Собирает метрики с нашего API мониторинга и экспортирует их в формате Prometheus
"""
import asyncio
import time
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, Optional
from monitoring.mylogger import Logger

logger = Logger(name="metrics_exporter", log_file="metrics_exporter.log")

class MetricsExporter:
    """Экспортер метрик для Prometheus"""
    
    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
        self.metrics_cache = {}
        self.last_update = 0
        self.cache_ttl = 30  # Кэшируем метрики на 30 секунд
        self.session = None  # aiohttp сессия будет создана при первом использовании
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получает или создает aiohttp сессию"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close_session(self):
        """Закрывает aiohttp сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        
    async def get_metrics(self) -> str:
        """Получает метрики в формате Prometheus"""
        try:
            # Получаем данные мониторинга
            monitoring_data = await self._fetch_monitoring_data()
            if not monitoring_data:
                return self._format_error_metrics()
            
            # Формируем метрики в формате Prometheus
            metrics = []
            
            # Системные метрики
            system = monitoring_data.get('system', {})
            metrics.extend([
                f"# HELP app_cpu_usage_percent CPU usage percentage",
                f"# TYPE app_cpu_usage_percent gauge",
                f"app_cpu_usage_percent {system.get('cpu_percent', 0)}",
                "",
                f"# HELP app_memory_usage_percent Memory usage percentage",
                f"# TYPE app_memory_usage_percent gauge",
                f"app_memory_usage_percent {system.get('memory_percent', 0)}",
                "",
                f"# HELP app_memory_available_mb Available memory in MB",
                f"# TYPE app_memory_available_mb gauge",
                f"app_memory_available_mb {system.get('memory_available_mb', 0)}",
                "",
                f"# HELP app_disk_usage_percent Disk usage percentage",
                f"# TYPE app_disk_usage_percent gauge",
                f"app_disk_usage_percent {system.get('disk_usage_percent', 0)}",
                ""
            ])
            
            # Статус приложения
            overall_status = monitoring_data.get('overall_status', 'unknown')
            status_value = self._status_to_number(overall_status)
            metrics.extend([
                f"# HELP app_status_overall Overall application status (0=healthy, 1=warning, 2=critical, 3=error)",
                f"# TYPE app_status_overall gauge",
                f"app_status_overall {status_value}",
                ""
            ])
            
            # Статус базы данных
            db_status = monitoring_data.get('database_status', 'unknown')
            db_status_value = 1 if db_status == 'healthy' else 0
            metrics.extend([
                f"# HELP app_database_status Database connection status (0=error, 1=healthy)",
                f"# TYPE app_database_status gauge",
                f"app_database_status {db_status_value}",
                ""
            ])
            
            # Метрики пула соединений
            pool_stats = monitoring_data.get('pool_stats', {})
            if 'error' not in pool_stats:
                metrics.extend([
                    f"# HELP app_pool_size Connection pool size",
                    f"# TYPE app_pool_size gauge",
                    f"app_pool_size {pool_stats.get('size', 0)}",
                    "",
                    f"# HELP app_pool_checked_in Connections checked in",
                    f"# TYPE app_pool_checked_in gauge",
                    f"app_pool_checked_in {pool_stats.get('checked_in', 0)}",
                    "",
                    f"# HELP app_pool_checked_out Connections checked out",
                    f"# TYPE app_pool_checked_out gauge",
                    f"app_pool_checked_out {pool_stats.get('checked_out', 0)}",
                    "",
                    f"# HELP app_pool_overflow Connection pool overflow",
                    f"# TYPE app_pool_overflow gauge",
                    f"app_pool_overflow {pool_stats.get('overflow', 0)}",
                    "",
                    f"# HELP app_pool_utilization_percent Connection pool utilization percentage",
                    f"# TYPE app_pool_utilization_percent gauge",
                    f"app_pool_utilization_percent {pool_stats.get('utilization_percent', 0)}",
                    ""
                ])
            
            # Временная метка
            timestamp = monitoring_data.get('timestamp', time.time())
            metrics.extend([
                f"# HELP app_metrics_timestamp Last metrics update timestamp",
                f"# TYPE app_metrics_timestamp gauge",
                f"app_metrics_timestamp {timestamp}",
                ""
            ])
            
            # Информация о мониторинге
            control_data = await self._fetch_control_data()
            if control_data:
                monitoring_active = 1 if control_data.get('monitoring_active', False) else 0
                metrics.extend([
                    f"# HELP app_monitoring_active Monitoring system status (0=inactive, 1=active)",
                    f"# TYPE app_monitoring_active gauge",
                    f"app_monitoring_active {monitoring_active}",
                    "",
                    f"# HELP app_monitoring_alerts_count Number of active alerts",
                    f"# TYPE app_monitoring_alerts_count gauge",
                    f"app_monitoring_alerts_count {control_data.get('last_alerts_count', 0)}",
                    ""
                ])
            
            return "\n".join(metrics)
            
        except Exception as e:
            logger.error(f"Ошибка получения метрик: {e}")
            return self._format_error_metrics()
    
    async def _fetch_monitoring_data(self) -> Optional[Dict[str, Any]]:
        """Получает данные мониторинга с API"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_url}/api/monitoring/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API вернул статус {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка HTTP-клиента при запросе к API: {e}")
            return None
        except asyncio.TimeoutError as e:
            logger.error(f"Таймаут при запросе к API: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе к API: {e}")
            return None
    
    async def _fetch_control_data(self) -> Optional[Dict[str, Any]]:
        """Получает данные управления мониторингом"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_url}/api/monitoring/control") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Control API вернул статус {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка HTTP-клиента при запросе к control API: {e}")
            return None
        except asyncio.TimeoutError as e:
            logger.error(f"Таймаут при запросе к control API: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе к control API: {e}")
            return None
    
    def _status_to_number(self, status: str) -> int:
        """Преобразует статус в числовое значение"""
        status_map = {
            'healthy': 0,
            'warning': 1,
            'critical': 2,
            'error': 3
        }
        return status_map.get(status, 3)
    
    def _format_error_metrics(self) -> str:
        """Форматирует метрики при ошибке"""
        return f"""# HELP app_status_overall Overall application status (0=healthy, 1=warning, 2=critical, 3=error)
# TYPE app_status_overall gauge
app_status_overall 3

# HELP app_metrics_timestamp Last metrics update timestamp
# TYPE app_metrics_timestamp gauge
app_metrics_timestamp {time.time()}
"""

# Глобальный экземпляр экспортера
exporter = MetricsExporter()
