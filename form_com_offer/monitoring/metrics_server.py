"""
HTTP сервер для экспорта метрик Prometheus
Запускается на отдельном порту и предоставляет эндпоинт /metrics
"""
import asyncio
import aiohttp
from aiohttp import web
import time
from monitoring.metrics_exporter import exporter
from monitoring.mylogger import Logger

logger = Logger(name="metrics_server", log_file="metrics_server.log")

class MetricsServer:
    """HTTP сервер для экспорта метрик Prometheus
    
    По умолчанию сервер доступен только на localhost (127.0.0.1).
    Для внешнего доступа необходимо явно указать host или настроить через переменные окружения.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9091):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Настройка маршрутов"""
        self.app.router.add_get('/', self.health_check)
        self.app.router.add_get('/metrics', self.metrics_endpoint)
        self.app.router.add_get('/health', self.health_check)
        
    async def health_check(self, request):
        """Эндпоинт проверки здоровья сервера метрик"""
        return web.json_response({
            "status": "healthy",
            "service": "metrics_exporter",
            "timestamp": time.time()
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
                content_type='text/plain; version=0.0.4; charset=utf-8'
            )
            
        except Exception as e:
            logger.error(f"Ошибка экспорта метрик: {e}")
            return web.Response(
                text="# ERROR: Failed to export metrics\n",
                status=500,
                content_type='text/plain; version=0.0.4; charset=utf-8'
            )
    
    async def start(self):
        """Запуск сервера"""
        try:
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, self.host, self.port)
            await site.start()
            
            logger.info(f"🚀 Сервер метрик запущен на http://{self.host}:{self.port}")
            logger.info(f"📊 Метрики доступны по адресу: http://{self.host}:{self.port}/metrics")
            
            return runner
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска сервера метрик: {e}")
            raise
    
    async def stop(self, runner):
        """Остановка сервера"""
        try:
            await runner.cleanup()
            logger.info("🛑 Сервер метрик остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки сервера метрик: {e}")

# Функция для запуска сервера
async def run_metrics_server(host: str = "127.0.0.1", port: int = 9091):
    """Запускает сервер метрик
    
    По умолчанию сервер доступен только на localhost (127.0.0.1).
    Для внешнего доступа необходимо явно указать host или настроить через переменные окружения.
    """
    server = MetricsServer(host, port)
    runner = await server.start()
    
    try:
        # Держим сервер запущенным
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        await server.stop(runner)

if __name__ == "__main__":
    # Запуск сервера метрик
    asyncio.run(run_metrics_server())
