# Verification Script for Botrix Integration Setup
# This script verifies all components are in place

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Botrix Setup Verification" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Check files exist
$requiredFiles = @(
    "tests\test_full_flow.py",
    "workers\worker_daemon.py",
    "docker-compose.yml",
    "Dockerfile.worker",
    "backend\Dockerfile",
    "scripts\run_integration_tests.ps1",
    "scripts\run_integration_tests.sh",
    "deployment\botrix-worker@.service",
    "WORKER_INTEGRATION_GUIDE.md",
    "QUICKSTART_WORKER.md"
)

Write-Host "Checking required files..." -ForegroundColor Yellow
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  OK $file" -ForegroundColor Green
    } else {
        Write-Host "  MISSING $file" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""
Write-Host "Checking test file content..." -ForegroundColor Yellow
$testContent = Get-Content "tests\test_full_flow.py" -Raw
if ($testContent -match "test_single_account_creation" -and $testContent -match "test_multiple_accounts_creation" -and $testContent -match "test_job_failure_handling") {
    Write-Host "  OK Integration tests include all required test cases" -ForegroundColor Green
} else {
    Write-Host "  FAIL Some test cases may be missing" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""
Write-Host "Checking worker daemon features..." -ForegroundColor Yellow
$workerContent = Get-Content "workers\worker_daemon.py" -Raw
$features = @{
    "BLPOP queue consumption" = "blpop"
    "Graceful shutdown" = "(SIGTERM|SIGINT)"
    "Health checks" = "health_check"
    "Retry logic" = "(retry_count|max_retries)"
    "Concurrent workers" = "worker_id"
}

foreach ($key in $features.Keys) {
    if ($workerContent -match $features[$key]) {
        Write-Host "  OK $key" -ForegroundColor Green
    } else {
        Write-Host "  FAIL $key (NOT FOUND)" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""
Write-Host "Checking Docker Compose services..." -ForegroundColor Yellow
$composeContent = Get-Content "docker-compose.yml" -Raw
$services = @("redis", "postgres", "backend", "worker")
foreach ($service in $services) {
    if ($composeContent -match "$service`:") {
        Write-Host "  OK $service service defined" -ForegroundColor Green
    } else {
        Write-Host "  FAIL $service service (MISSING)" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""
Write-Host "Checking health check endpoints..." -ForegroundColor Yellow
if (Test-Path "backend\main.go") {
    $mainContent = Get-Content "backend\main.go" -Raw
    $healthEndpoints = @("/health", "/health/ping", "/health/ready", "/health/live")
    foreach ($endpoint in $healthEndpoints) {
        $escapedEndpoint = [regex]::Escape($endpoint)
        if ($mainContent -match $escapedEndpoint) {
            Write-Host "  OK $endpoint endpoint" -ForegroundColor Green
        } else {
            Write-Host "  FAIL $endpoint endpoint (MISSING)" -ForegroundColor Red
            $allGood = $false
        }
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "  ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Install dependencies: pip install -r requirements.txt"
    Write-Host "  2. Start Redis: docker run -d -p 6379:6379 redis:7-alpine"
    Write-Host "  3. Run integration tests: .\scripts\run_integration_tests.ps1"
    Write-Host "  4. Or start full stack: docker-compose up -d"
    Write-Host ""
} else {
    Write-Host "  SOME CHECKS FAILED" -ForegroundColor Red
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Please review the errors above." -ForegroundColor Red
}
