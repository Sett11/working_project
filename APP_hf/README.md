# APP_hf

## Развертывание на удаленном сервере

### Требования
- Docker
- Docker Compose

### Инструкция по развертыванию

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd APP_hf
```

2. Сделайте скрипт развертывания исполняемым:
```bash
chmod +x deploy.sh
```

3. Запустите скрипт развертывания:
```bash
./deploy.sh
```

### Доступ к приложению
- Frontend: http://86.110.212.192:7861
- Backend: http://86.110.212.192:8000

### Мониторинг
- Проверка статуса контейнеров: `docker-compose ps`
- Просмотр логов: `docker-compose logs -f`

### Остановка приложения
```bash
docker-compose down
``` 