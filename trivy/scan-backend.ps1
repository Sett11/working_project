# =============================================================================
# Trivy Security Scanner - Scan Backend Only
# =============================================================================
# Описание: Сканирование только Backend образа
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

$imageName = "${projectName}_backend"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$reportsDir = Join-Path $PSScriptRoot "reports"

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

# Создаём директорию если не существует
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

# Файлы отчётов
$jsonReport = Join-Path $reportsDir "scan_backend_${timestamp}.json"
$tableReport = Join-Path $reportsDir "scan_backend_${timestamp}.txt"

# Сканирование
docker run --rm `
    -v /var/run/docker.sock:/var/run/docker.sock `
    -v "${reportsDir}:/reports" `
    aquasec/trivy:latest `
    image `
    --severity CRITICAL,HIGH,MEDIUM `
    --format table `
    --output /reports/temp_backend.txt `
    $imageName

if (Test-Path (Join-Path $reportsDir "temp_backend.txt")) {
    Move-Item (Join-Path $reportsDir "temp_backend.txt") $tableReport -Force
}

# JSON отчёт
docker run --rm `
    -v /var/run/docker.sock:/var/run/docker.sock `
    -v "${reportsDir}:/reports" `
    aquasec/trivy:latest `
    image `
    --severity CRITICAL,HIGH,MEDIUM,LOW `
    --format json `
    --output /reports/temp_backend.json `
    $imageName

if (Test-Path (Join-Path $reportsDir "temp_backend.json")) {
    Move-Item (Join-Path $reportsDir "temp_backend.json") $jsonReport -Force
}

Write-Host "`n✓ Сканирование завершено!" -ForegroundColor $COLOR_GREEN
Write-Host "  Отчёты сохранены в: $reportsDir" -ForegroundColor $COLOR_CYAN
Write-Host "  • JSON:  $jsonReport" -ForegroundColor White
Write-Host "  • Table: $tableReport" -ForegroundColor White
Write-Host ""

