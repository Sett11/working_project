# =============================================================================
# Trivy Security Scanner - Scan All Containers
# =============================================================================
# Описание: Автоматическое сканирование всех Docker образов проекта
# Автор: Security Team
# Дата создания: 2025-10-08
# =============================================================================

# Настройки скрипта
$ErrorActionPreference = "Continue"
$ProgressPreference = "Continue"

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

# Цвета для вывода
$COLOR_GREEN = "Green"
$COLOR_RED = "Red"
$COLOR_YELLOW = "Yellow"
$COLOR_CYAN = "Cyan"
$COLOR_MAGENTA = "Magenta"

# Получаем COMPOSE_PROJECT_NAME из .env или используем значение по умолчанию
$envFile = Join-Path $PSScriptRoot ".." ".env"
$projectName = "working_project"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^COMPOSE_PROJECT_NAME=(.+)$") {
            $projectName = $matches[1]
            Write-Host "✓ Найден COMPOSE_PROJECT_NAME: $projectName" -ForegroundColor $COLOR_GREEN
        }
    }
}

# Образы для сканирования
$images = @{
    "Backend" = "${projectName}_backend"
    "Frontend" = "${projectName}_frontend"
    "Database" = "postgres:15-alpine"
}

# Директории для отчётов и логов
$reportsDir = Join-Path $PSScriptRoot "reports"
$logsDir = Join-Path $PSScriptRoot "logs"
$cacheDir = Join-Path $PSScriptRoot "cache"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$summaryFile = Join-Path $reportsDir "summary_${timestamp}.txt"

# Убедимся, что директории существуют
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}
if (-not (Test-Path $cacheDir)) {
    New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
}

# =============================================================================
# ФУНКЦИИ
# =============================================================================

function Write-Banner {
    param([string]$text)
    Write-Host "`n$("=" * 80)" -ForegroundColor $COLOR_CYAN
    Write-Host "  $text" -ForegroundColor $COLOR_CYAN
    Write-Host "$("=" * 80)`n" -ForegroundColor $COLOR_CYAN
}

function Write-Section {
    param([string]$text)
    Write-Host "`n$("-" * 80)" -ForegroundColor $COLOR_MAGENTA
    Write-Host "  $text" -ForegroundColor $COLOR_MAGENTA
    Write-Host "$("-" * 80)" -ForegroundColor $COLOR_MAGENTA
}

function Check-DockerImage {
    param([string]$imageName)
    
    $exists = docker images -q $imageName 2>$null
    return $null -ne $exists -and $exists -ne ""
}

function Scan-Image {
    param(
        [string]$imageName,
        [string]$displayName
    )
    
    Write-Section "Сканирование: $displayName"
    
    # Проверяем существование образа
    if (-not (Check-DockerImage $imageName)) {
        Write-Host "⚠ Образ '$imageName' не найден. Пропускаем..." -ForegroundColor $COLOR_YELLOW
        return @{
            Name = $displayName
            Image = $imageName
            Status = "Skipped"
            Critical = 0
            High = 0
            Medium = 0
            Low = 0
        }
    }
    
    Write-Host "✓ Образ найден: $imageName" -ForegroundColor $COLOR_GREEN
    Write-Host "  Начинаем сканирование..." -ForegroundColor $COLOR_CYAN
    
    # Файлы для отчётов
    $safeImageName = $imageName -replace "[:/]", "_"
    $jsonReport = Join-Path $reportsDir "scan_${safeImageName}_${timestamp}.json"
    $tableReport = Join-Path $reportsDir "scan_${safeImageName}_${timestamp}.txt"
    $htmlReport = Join-Path $reportsDir "scan_${safeImageName}_${timestamp}.html"
    
    try {
        # Сканирование с выводом в таблицу
        Write-Host "`n  → Генерация отчёта (таблица)..." -ForegroundColor $COLOR_CYAN
        docker run --rm `
            -v /var/run/docker.sock:/var/run/docker.sock `
            -v "${PSScriptRoot}:/config:ro" `
            -v "${reportsDir}:/reports" `
            -v "${cacheDir}:/cache" `
            -e TRIVY_CACHE_DIR=/cache `
            aquasec/trivy:0.63.0 `
            image `
            --severity CRITICAL,HIGH,MEDIUM `
            --format table `
            --output /reports/temp_table.txt `
            $imageName
        
        # Копируем временный файл
        if (Test-Path (Join-Path $reportsDir "temp_table.txt")) {
            Move-Item (Join-Path $reportsDir "temp_table.txt") $tableReport -Force
        }
        
        # Сканирование с выводом в JSON для детального анализа
        Write-Host "  → Генерация отчёта (JSON)..." -ForegroundColor $COLOR_CYAN
        docker run --rm `
            -v /var/run/docker.sock:/var/run/docker.sock `
            -v "${PSScriptRoot}:/config:ro" `
            -v "${reportsDir}:/reports" `
            -v "${cacheDir}:/cache" `
            -e TRIVY_CACHE_DIR=/cache `
            aquasec/trivy:0.63.0 `
            image `
            --severity CRITICAL,HIGH,MEDIUM,LOW `
            --format json `
            --output /reports/temp_json.json `
            $imageName
        
        # Копируем временный файл
        if (Test-Path (Join-Path $reportsDir "temp_json.json")) {
            Move-Item (Join-Path $reportsDir "temp_json.json") $jsonReport -Force
        }
        
        # Парсим результаты из JSON
        $results = @{
            Name = $displayName
            Image = $imageName
            Status = "Completed"
            Critical = 0
            High = 0
            Medium = 0
            Low = 0
        }
        
        if (Test-Path $jsonReport) {
            $jsonContent = Get-Content $jsonReport -Raw | ConvertFrom-Json
            
            foreach ($result in $jsonContent.Results) {
                if ($result.Vulnerabilities) {
                    foreach ($vuln in $result.Vulnerabilities) {
                        switch ($vuln.Severity) {
                            "CRITICAL" { $results.Critical++ }
                            "HIGH"     { $results.High++ }
                            "MEDIUM"   { $results.Medium++ }
                            "LOW"      { $results.Low++ }
                        }
                    }
                }
            }
        }
        
        # Выводим результаты
        Write-Host "`n  📊 Результаты сканирования:" -ForegroundColor $COLOR_CYAN
        Write-Host "     🔴 CRITICAL: $($results.Critical)" -ForegroundColor $(if ($results.Critical -gt 0) { $COLOR_RED } else { $COLOR_GREEN })
        Write-Host "     🟠 HIGH:     $($results.High)" -ForegroundColor $(if ($results.High -gt 0) { $COLOR_RED } else { $COLOR_GREEN })
        Write-Host "     🟡 MEDIUM:   $($results.Medium)" -ForegroundColor $(if ($results.Medium -gt 0) { $COLOR_YELLOW } else { $COLOR_GREEN })
        Write-Host "     🔵 LOW:      $($results.Low)" -ForegroundColor $COLOR_CYAN
        
        Write-Host "`n  ✓ Отчёты сохранены:" -ForegroundColor $COLOR_GREEN
        Write-Host "     • JSON:  $jsonReport" -ForegroundColor $COLOR_CYAN
        Write-Host "     • Table: $tableReport" -ForegroundColor $COLOR_CYAN
        
        return $results
    }
    catch {
        Write-Host "✗ Ошибка при сканировании: $_" -ForegroundColor $COLOR_RED
        return @{
            Name = $displayName
            Image = $imageName
            Status = "Error"
            Critical = 0
            High = 0
            Medium = 0
            Low = 0
            Error = $_.Exception.Message
        }
    }
}

# =============================================================================
# ГЛАВНАЯ ЛОГИКА
# =============================================================================

Write-Banner "🛡️  TRIVY SECURITY SCANNER - Сканирование всех образов"

Write-Host "📋 Конфигурация:" -ForegroundColor $COLOR_CYAN
Write-Host "   • Проект: $projectName" -ForegroundColor White
Write-Host "   • Образов для сканирования: $($images.Count)" -ForegroundColor White
Write-Host "   • Директория отчётов: $reportsDir" -ForegroundColor White
Write-Host "   • Временная метка: $timestamp" -ForegroundColor White

# Проверяем наличие Docker
Write-Section "Проверка окружения"
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker: $dockerVersion" -ForegroundColor $COLOR_GREEN
}
catch {
    Write-Host "✗ Docker не найден! Установите Docker Desktop." -ForegroundColor $COLOR_RED
    exit 1
}

# Проверяем наличие образа Trivy
Write-Host "  Проверка образа Trivy..." -ForegroundColor $COLOR_CYAN
$pullOutput = docker pull aquasec/trivy:0.63.0 2>&1
$pullExitCode = $LASTEXITCODE

if ($pullExitCode -ne 0) {
    Write-Host "✗ Не удалось загрузить образ Trivy!" -ForegroundColor $COLOR_RED
    Write-Host "Вывод команды docker pull:" -ForegroundColor $COLOR_YELLOW
    Write-Host $pullOutput -ForegroundColor $COLOR_YELLOW
    exit 1
}

Write-Host "✓ Образ Trivy обновлён" -ForegroundColor $COLOR_GREEN

# Сканируем все образы
$allResults = @()
foreach ($entry in $images.GetEnumerator()) {
    $result = Scan-Image -imageName $entry.Value -displayName $entry.Key
    $allResults += $result
    Start-Sleep -Seconds 1
}

# Генерируем итоговый отчёт
Write-Banner "📊 ИТОГОВЫЙ ОТЧЁТ"

$summary = @"
================================================================================
                    TRIVY SECURITY SCAN SUMMARY
================================================================================
Дата сканирования: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Проект: $projectName

$(foreach ($result in $allResults) {
@"
--------------------------------------------------------------------------------
$($result.Name) ($($result.Image))
--------------------------------------------------------------------------------
Статус: $($result.Status)
Уязвимости:
  🔴 CRITICAL: $($result.Critical)
  🟠 HIGH:     $($result.High)
  🟡 MEDIUM:   $($result.Medium)
  🔵 LOW:      $($result.Low)

"@
})

================================================================================
ОБЩАЯ СТАТИСТИКА
================================================================================
Всего образов: $($allResults.Count)
Просканировано: $($allResults | Where-Object { $_.Status -eq "Completed" } | Measure-Object | Select-Object -ExpandProperty Count)
Пропущено: $($allResults | Where-Object { $_.Status -eq "Skipped" } | Measure-Object | Select-Object -ExpandProperty Count)
Ошибок: $($allResults | Where-Object { $_.Status -eq "Error" } | Measure-Object | Select-Object -ExpandProperty Count)

Всего уязвимостей:
  🔴 CRITICAL: $(($allResults | Measure-Object -Property Critical -Sum).Sum)
  🟠 HIGH:     $(($allResults | Measure-Object -Property High -Sum).Sum)
  🟡 MEDIUM:   $(($allResults | Measure-Object -Property Medium -Sum).Sum)
  🔵 LOW:      $(($allResults | Measure-Object -Property Low -Sum).Sum)

================================================================================
РЕКОМЕНДАЦИИ
================================================================================
$( if ((($allResults | Measure-Object -Property Critical -Sum).Sum) -gt 0) {
    "⚠️  ВНИМАНИЕ! Обнаружены CRITICAL уязвимости! Требуется немедленное исправление!"
} elseif ((($allResults | Measure-Object -Property High -Sum).Sum) -gt 0) {
    "⚠️  Обнаружены HIGH уязвимости. Рекомендуется исправить в ближайшее время."
} else {
    "✓ Критических уязвимостей не обнаружено."
})

Детальные отчёты сохранены в: $reportsDir
================================================================================
"@

# Сохраняем итоговый отчёт
$summary | Out-File -FilePath $summaryFile -Encoding UTF8
Write-Host $summary -ForegroundColor White

Write-Host "`n✓ Итоговый отчёт сохранён: $summaryFile" -ForegroundColor $COLOR_GREEN

# Определяем код возврата
$totalCritical = ($allResults | Measure-Object -Property Critical -Sum).Sum
$totalHigh = ($allResults | Measure-Object -Property High -Sum).Sum

if ($totalCritical -gt 0) {
    Write-Host "`n❌ СКАНИРОВАНИЕ ЗАВЕРШЕНО С КРИТИЧЕСКИМИ УЯЗВИМОСТЯМИ" -ForegroundColor $COLOR_RED
    exit 1
} elseif ($totalHigh -gt 0) {
    Write-Host "`n⚠️  СКАНИРОВАНИЕ ЗАВЕРШЕНО С HIGH УЯЗВИМОСТЯМИ" -ForegroundColor $COLOR_YELLOW
    exit 0
} else {
    Write-Host "`n✅ СКАНИРОВАНИЕ УСПЕШНО ЗАВЕРШЕНО" -ForegroundColor $COLOR_GREEN
    exit 0
}

