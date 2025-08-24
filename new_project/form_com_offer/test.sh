#!/bin/bash

# Скрипт для запуска тестов в Docker окружении
# Использование: ./test.sh [опции]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка, что docker-compose.yml существует
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml не найден в текущей директории"
    exit 1
fi

# Проверка, что контейнеры запущены
if ! docker-compose ps | grep -q "Up"; then
    print_warning "Контейнеры не запущены. Запускаю..."
    docker-compose up -d
    sleep 5
fi

# Функция для показа справки
show_help() {
    echo "Использование: $0 [опции]"
    echo ""
    echo "Опции:"
    echo "  --all              Запустить все тесты"
    echo "  --unit             Запустить только unit тесты"
    echo "  --api              Запустить только API тесты"
    echo "  --database         Запустить только тесты базы данных"
    echo "  --frontend         Запустить только тесты фронтенда"
    echo "  --pdf              Запустить только тесты PDF генерации"
    echo "  --integration      Запустить только интеграционные тесты"
    echo "  --coverage         Запустить тесты с покрытием кода"
    echo "  --specific <test>  Запустить конкретный тест"
    echo "  --help             Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 --all"
    echo "  $0 --unit"
    echo "  $0 --api"
    echo "  $0 --coverage"
    echo "  $0 --specific tests/test_api.py::test_health_endpoint"
}

# Функция для запуска тестов
run_tests() {
    local test_type="$1"
    local test_args="$2"
    
    print_info "Запуск тестов: $test_type"
    
    if [ -n "$test_args" ]; then
        docker-compose exec backend python run_tests.py $test_args
    else
        docker-compose exec backend python run_tests.py --$test_type
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Тесты $test_type завершены успешно"
    else
        print_error "Тесты $test_type завершились с ошибками"
        exit 1
    fi
}

# Обработка аргументов
case "${1:-}" in
    --all)
        run_tests "all"
        ;;
    --unit)
        run_tests "unit"
        ;;
    --api)
        run_tests "api"
        ;;
    --database)
        run_tests "database"
        ;;
    --frontend)
        run_tests "frontend"
        ;;
    --pdf)
        run_tests "pdf"
        ;;
    --integration)
        run_tests "integration"
        ;;
    --coverage)
        run_tests "coverage"
        ;;
    --specific)
        if [ -z "$2" ]; then
            print_error "Не указан конкретный тест для --specific"
            exit 1
        fi
        run_tests "specific" "--specific $2"
        ;;
    --help|-h)
        show_help
        ;;
    "")
        print_info "Запуск всех тестов (по умолчанию)"
        run_tests "all"
        ;;
    *)
        print_error "Неизвестная опция: $1"
        show_help
        exit 1
        ;;
esac
