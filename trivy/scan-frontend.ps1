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
            $projectName = $matches[1].Trim()
        }
    }
}

$imageName = "${projectName}_frontend"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$reportsDir = Join-Path $PSScriptRoot "reports"
$cacheDir = Join-Path $PSScriptRoot "cache"

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

# Создаём директории если не существуют
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}
if (-not (Test-Path $cacheDir)) {
    New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
}

# Файлы отчётов
$jsonReport = Join-Path $reportsDir "scan_frontend_${timestamp}.json"
$tableReport = Join-Path $reportsDir "scan_frontend_${timestamp}.txt"

# Сканирование
docker run --rm `
    -v /var/run/docker.sock:/var/run/docker.sock `
    -v "${reportsDir}:/reports" `
    -v "${cacheDir}:/cache" `
    -e TRIVY_CACHE_DIR=/cache `
    aquasec/trivy:0.63.0 `
    image `
    --severity CRITICAL,HIGH,MEDIUM `
    --format table `
    --output /reports/temp_frontend.txt `
    $imageName

$tempTableFile = Join-Path $reportsDir "temp_frontend.txt"
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Ошибка при сканировании (table format)!" -ForegroundColor $COLOR_RED
    Write-Host "  Код выхода: $LASTEXITCODE" -ForegroundColor $COLOR_RED
    exit 1
}

if (-not (Test-Path $tempTableFile)) {
    Write-Host "`n✗ Временный файл отчёта не найден: $tempTableFile" -ForegroundColor $COLOR_RED
    exit 1
}

Move-Item $tempTableFile $tableReport -Force

# JSON отчёт
docker run --rm `
    -v /var/run/docker.sock:/var/run/docker.sock `
    -v "${reportsDir}:/reports" `
    -v "${cacheDir}:/cache" `
    -e TRIVY_CACHE_DIR=/cache `
    aquasec/trivy:0.63.0 `
    image `
    --severity CRITICAL,HIGH,MEDIUM,LOW `
    --format json `
    --output /reports/temp_frontend.json `
    $imageName

$tempJsonFile = Join-Path $reportsDir "temp_frontend.json"
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Ошибка при сканировании (JSON format)!" -ForegroundColor $COLOR_RED
    Write-Host "  Код выхода: $LASTEXITCODE" -ForegroundColor $COLOR_RED
    exit 1
}

if (-not (Test-Path $tempJsonFile)) {
    Write-Host "`n✗ Временный файл отчёта не найден: $tempJsonFile" -ForegroundColor $COLOR_RED
    exit 1
}

Move-Item $tempJsonFile $jsonReport -Force

Write-Host "`n✓ Сканирование завершено!" -ForegroundColor $COLOR_GREEN
Write-Host "  Отчёты сохранены в: $reportsDir" -ForegroundColor $COLOR_CYAN
Write-Host "  • JSON:  $jsonReport" -ForegroundColor White
Write-Host "  • Table: $tableReport" -ForegroundColor White
Write-Host ""

