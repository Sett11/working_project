"""
HTTP сервер для экспорта метрик Prometheus
Запускается на отдельном порту и предоставляет эндпоинт /metrics
"""
import asyncio
import signal
import aiohttp
from aiohttp import web
import time
import os
from pathlib import Path
from metrics_exporter import exporter
from mylogger import Logger

# Создаем директорию logs перед инициализацией Logger
logs_dir = Path("logs")
logs_dir.mkdir(parents=True, exist_ok=True)

logger = Logger(name="metrics_server", log_file="metrics_server.log")

# Глобальная переменная для события остановки
_stop_event = None

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global _stop_event
    if _stop_event:
        logger.info(f"📡 Получен сигнал {signum}, инициируем остановку сервера...")
        _stop_event.set()
    else:
        logger.warning(f"Получен сигнал {signum}, но stop_event не инициализирован")

class MetricsServer:
    """HTTP сервер для экспорта метрик Prometheus
    
    По умолчанию сервер доступен только на localhost (127.0.0.1).
    Для внешнего доступа необходимо явно указать host или настроить через переменные окружения.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 9091, stop_event: asyncio.Event = None):
        self.host = host
        self.port = port
        self.stop_event = stop_event or asyncio.Event()
        self.app = web.Application()
        self.runner = None
        self._running = False
        self.setup_routes()
        
    def setup_routes(self):
        """Настройка маршрутов"""
        self.app.router.add_get('/', self.health_check)
        self.app.router.add_get('/metrics', self.metrics_endpoint)
        self.app.router.add_get('/health', self.health_check)
        
    def is_running(self) -> bool:
        """Проверяет, запущен ли сервер"""
        return self._running and self.runner is not None
        
    async def health_check(self, request):
        """Эндпоинт проверки здоровья сервера метрик"""
        return web.json_response({
            "status": "healthy" if self.is_running() else "stopping",
            "service": "metrics_exporter",
            "timestamp": time.time(),
            "running": self.is_running()
        })
    
    async def metrics_endpoint(self, request):
        """Эндпоинт для экспорта метрик в формате Prometheus"""
        try:
            start_time = time.time()
            
            # Получаем метрики
            metrics = await exporter.get_metrics()
            
            # Логируем время выполнения
            duration = time.time() - start_time
            logger.debug(f"Метрики экспортированы за {duration:.3f} сек")
            
            # Возвращаем метрики в формате Prometheus
            return web.Response(
                text=metrics,
                content_type='text/plain; version=0.0.4',
                charset='utf-8'
            )
            
        except Exception as e:
            logger.error(f"Ошибка экспорта метрик: {e}")
            return web.Response(
                text="# ERROR: Failed to export metrics\n",
                status=500,
                content_type='text/plain; version=0.0.4',
                charset='utf-8'
            )
    
    async def start(self):
        """Запуск сервера"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            site = web.TCPSite(self.runner, self.host, self.port)
            await site.start()
            
            self._running = True
            logger.info(f"🚀 Сервер метрик запущен на http://{self.host}:{self.port}")
            logger.info(f"📊 Метрики доступны по адресу: http://{self.host}:{self.port}/metrics")
            
            return self.runner
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска сервера метрик: {e}")
            self._running = False
            raise
    
    async def stop(self, runner=None):
        """Остановка сервера"""
        try:
            logger.info("🔄 Начинаем остановку сервера метрик...")
            
            # Устанавливаем событие остановки для пробуждения основного цикла
            self.stop_event.set()
            self._running = False
            
            # Останавливаем runner
            runner_to_stop = runner or self.runner
            if runner_to_stop:
                await runner_to_stop.cleanup()
                logger.info("🛑 Сервер метрик остановлен")
            else:
                logger.warning("⚠️ Runner не найден для остановки")
        except Exception as e:
            logger.error(f"Ошибка остановки сервера метрик: {e}")
            self._running = False

# Функция для запуска сервера
async def run_metrics_server(host: str = "0.0.0.0", port: int = 9091, stop_event: asyncio.Event = None):
    """Запускает сервер метрик
    
    Args:
        host: Хост для привязки сервера (по умолчанию 0.0.0.0)
        port: Порт для привязки сервера (по умолчанию 9091)
        stop_event: Событие для сигнализации остановки сервера
    
    По умолчанию сервер доступен на всех интерфейсах (0.0.0.0).
    Для ограничения доступа только к localhost используйте host="127.0.0.1".
    """
    global _stop_event
    
    # Создаем событие остановки, если не передано
    if stop_event is None:
        stop_event = asyncio.Event()
    
    # Устанавливаем глобальную переменную для обработчика сигналов
    _stop_event = stop_event
    
    # Настраиваем обработчики сигналов для graceful shutdown
    try:
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # SIGTERM
        logger.debug("🔧 Обработчики сигналов настроены")
    except Exception as e:
        logger.warning(f"Не удалось настроить обработчики сигналов: {e}")
    
    server = MetricsServer(host, port, stop_event)
    runner = await server.start()
    
    try:
        logger.info("⏳ Сервер метрик ожидает сигнала остановки...")
        # Ожидаем сигнала остановки вместо бесконечного цикла
        await stop_event.wait()
        logger.info("📡 Получен сигнал остановки сервера метрик")
    except KeyboardInterrupt:
        logger.info("⌨️ Получен сигнал KeyboardInterrupt")
        stop_event.set()
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка в сервере метрик: {e}")
        stop_event.set()
    finally:
        await server.stop(runner)

if __name__ == "__main__":
    # Запуск сервера метрик
    asyncio.run(run_metrics_server())
