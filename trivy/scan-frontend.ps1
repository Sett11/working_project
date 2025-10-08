# =============================================================================
# Trivy Security Scanner - Scan Frontend Only
# =============================================================================
# Описание: Сканирование только Frontend образа
# Автор: Security Team
# Дата создания: 2025-10-08
# =============================================================================

$ErrorActionPreference = "Continue"

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

$imageName = "${projectName}_frontend"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$reportsDir = Join-Path $PSScriptRoot "reports"

Write-Host "`n🛡️  TRIVY - Сканирование Frontend образа`n" -ForegroundColor $COLOR_CYAN
Write-Host "Образ: $imageName" -ForegroundColor White

# Проверяем существование образа
$exists = docker images -q $imageName 2>$null
if (-not $exists) {
    Write-Host "✗ Образ '$imageName' не найден!" -ForegroundColor $COLOR_RED
    Write-Host "  Frontend образ будет собран только перед деплоем." -ForegroundColor $COLOR_YELLOW
    Write-Host "  Запустите: docker-compose build frontend" -ForegroundColor $COLOR_YELLOW
    exit 1
}

Write-Host "✓ Образ найден" -ForegroundColor $COLOR_GREEN
Write-Host "`nЗапуск сканирования...`n" -ForegroundColor $COLOR_CYAN

# Создаём директорию если не существует
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

# Файлы отчётов
$jsonReport = Join-Path $reportsDir "scan_frontend_${timestamp}.json"
$tableReport = Join-Path $reportsDir "scan_frontend_${timestamp}.txt"

# Сканирование
docker run --rm `
    -v /var/run/docker.sock:/var/run/docker.sock `
    -v "${reportsDir}:/reports" `
    aquasec/trivy:latest `
    image `
    --severity CRITICAL,HIGH,MEDIUM `
    --format table `
    --output /reports/temp_frontend.txt `
    $imageName

if (Test-Path (Join-Path $reportsDir "temp_frontend.txt")) {
    Move-Item (Join-Path $reportsDir "temp_frontend.txt") $tableReport -Force
}

# JSON отчёт
docker run --rm `
    -v /var/run/docker.sock:/var/run/docker.sock `
    -v "${reportsDir}:/reports" `
    aquasec/trivy:latest `
    image `
    --severity CRITICAL,HIGH,MEDIUM,LOW `
    --format json `
    --output /reports/temp_frontend.json `
    $imageName

if (Test-Path (Join-Path $reportsDir "temp_frontend.json")) {
    Move-Item (Join-Path $reportsDir "temp_frontend.json") $jsonReport -Force
}

Write-Host "`n✓ Сканирование завершено!" -ForegroundColor $COLOR_GREEN
Write-Host "  Отчёты сохранены в: $reportsDir" -ForegroundColor $COLOR_CYAN
Write-Host "  • JSON:  $jsonReport" -ForegroundColor White
Write-Host "  • Table: $tableReport" -ForegroundColor White
Write-Host ""

