# =============================================================================
# Trivy Security Scanner - Scan Backend Only
# =============================================================================
# Описание: Сканирование только Backend образа
# Автор: Security Team
# Дата создания: 2025-10-08
# =============================================================================

$ErrorActionPreference = "Stop"

# Цвета
$COLOR_GREEN = "Green"
$COLOR_RED = "Red"
$COLOR_YELLOW = "Yellow"
$COLOR_CYAN = "Cyan"

# Получаем имя проекта
$envFile = Join-Path $PSScriptRoot ".." ".env"
$projectName = "working_project"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^COMPOSE_PROJECT_NAME=(.+)$") {
            $projectName = $matches[1]
        }
    }
}

$imageName = "${projectName}_backend"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$reportsDir = Join-Path $PSScriptRoot "reports"
$cacheDir = Join-Path $PSScriptRoot "cache"

Write-Host "`n🛡️  TRIVY - Сканирование Backend образа`n" -ForegroundColor $COLOR_CYAN
Write-Host "Образ: $imageName" -ForegroundColor White

# Проверяем существование образа
$exists = docker images -q $imageName 2>$null
if (-not $exists) {
    Write-Host "✗ Образ '$imageName' не найден!" -ForegroundColor $COLOR_RED
    Write-Host "  Запустите: docker-compose build backend" -ForegroundColor $COLOR_YELLOW
    exit 1
}

Write-Host "✓ Образ найден" -ForegroundColor $COLOR_GREEN
Write-Host "`nЗапуск сканирования...`n" -ForegroundColor $COLOR_CYAN

# Создаём директории если не существуют
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}
if (-not (Test-Path $cacheDir)) {
    New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
}

# Файлы отчётов
$jsonReport = Join-Path $reportsDir "scan_backend_${timestamp}.json"
$tableReport = Join-Path $reportsDir "scan_backend_${timestamp}.txt"

# Сканирование (table format)
Write-Host "Запуск сканирования (table format)..." -ForegroundColor $COLOR_CYAN

try {
    docker run --rm `
        -v /var/run/docker.sock:/var/run/docker.sock `
        -v "${reportsDir}:/reports" `
        -v "${cacheDir}:/cache" `
        -e TRIVY_CACHE_DIR=/cache `
        aquasec/trivy:0.63.0 `
        image `
        --severity CRITICAL,HIGH,MEDIUM `
        --format table `
        --output /reports/temp_backend.txt `
        $imageName
    
    # Проверяем exit code Docker команды
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Ошибка: Сканирование Trivy (table) завершилось с кодом $LASTEXITCODE" -ForegroundColor $COLOR_RED
        # Удаляем частичный файл если он существует
        $tempTableFile = Join-Path $reportsDir "temp_backend.txt"
        if (Test-Path $tempTableFile) {
            Remove-Item $tempTableFile -Force
            Write-Host "  Удалён частичный файл: temp_backend.txt" -ForegroundColor $COLOR_YELLOW
        }
        exit 1
    }
    
    # Проверяем существование и размер файла отчёта
    $tempTableFile = Join-Path $reportsDir "temp_backend.txt"
    if (Test-Path $tempTableFile) {
        $fileInfo = Get-Item $tempTableFile
        if ($fileInfo.Length -eq 0) {
            Write-Host "✗ Ошибка: Файл отчёта temp_backend.txt пуст" -ForegroundColor $COLOR_RED
            Remove-Item $tempTableFile -Force
            exit 1
        }
        Move-Item $tempTableFile $tableReport -Force
        Write-Host "✓ Table отчёт сохранён успешно" -ForegroundColor $COLOR_GREEN
    } else {
        Write-Host "✗ Ошибка: Файл отчёта temp_backend.txt не создан" -ForegroundColor $COLOR_RED
        exit 1
    }
} catch {
    Write-Host "✗ Критическая ошибка при сканировании (table): $_" -ForegroundColor $COLOR_RED
    exit 1
}

# JSON отчёт
Write-Host "`nЗапуск сканирования (JSON format)..." -ForegroundColor $COLOR_CYAN

try {
    docker run --rm `
        -v /var/run/docker.sock:/var/run/docker.sock `
        -v "${reportsDir}:/reports" `
        -v "${cacheDir}:/cache" `
        -e TRIVY_CACHE_DIR=/cache `
        aquasec/trivy:0.63.0 `
        image `
        --severity CRITICAL,HIGH,MEDIUM,LOW `
        --format json `
        --output /reports/temp_backend.json `
        $imageName
    
    # Проверяем exit code Docker команды
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Ошибка: Сканирование Trivy (JSON) завершилось с кодом $LASTEXITCODE" -ForegroundColor $COLOR_RED
        # Удаляем частичный файл если он существует
        $tempJsonFile = Join-Path $reportsDir "temp_backend.json"
        if (Test-Path $tempJsonFile) {
            Remove-Item $tempJsonFile -Force
            Write-Host "  Удалён частичный файл: temp_backend.json" -ForegroundColor $COLOR_YELLOW
        }
        exit 1
    }
    
    # Проверяем существование и размер файла отчёта
    $tempJsonFile = Join-Path $reportsDir "temp_backend.json"
    if (Test-Path $tempJsonFile) {
        $fileInfo = Get-Item $tempJsonFile
        if ($fileInfo.Length -eq 0) {
            Write-Host "✗ Ошибка: Файл отчёта temp_backend.json пуст" -ForegroundColor $COLOR_RED
            Remove-Item $tempJsonFile -Force
            exit 1
        }
        Move-Item $tempJsonFile $jsonReport -Force
        Write-Host "✓ JSON отчёт сохранён успешно" -ForegroundColor $COLOR_GREEN
    } else {
        Write-Host "✗ Ошибка: Файл отчёта temp_backend.json не создан" -ForegroundColor $COLOR_RED
        exit 1
    }
} catch {
    Write-Host "✗ Критическая ошибка при сканировании (JSON): $_" -ForegroundColor $COLOR_RED
    exit 1
}

Write-Host "`n✓ Сканирование завершено!" -ForegroundColor $COLOR_GREEN
Write-Host "  Отчёты сохранены в: $reportsDir" -ForegroundColor $COLOR_CYAN
Write-Host "  • JSON:  $jsonReport" -ForegroundColor White
Write-Host "  • Table: $tableReport" -ForegroundColor White
Write-Host ""

