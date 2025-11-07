# Integration Test Runner for Botrix (PowerShell)
#
# This script:
# 1. Starts all required services (Redis, Backend, Worker)
# 2. Waits for services to be healthy
# 3. Runs integration tests
# 4. Tears down services
# 5. Reports results
#
# Usage:
#   .\scripts\run_integration_tests.ps1 [-KeepAlive] [-Verbose]
#
# Options:
#   -KeepAlive    Don't tear down services after tests
#   -Verbose      Show detailed output
#

param(
    [switch]$KeepAlive,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $ProjectDir "docker-compose.yml"
$TestFile = Join-Path $ProjectDir "tests\test_full_flow.py"

$TestsPassed = $false

# Functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Wait-ForService {
    param(
        [string]$ServiceName,
        [int]$MaxAttempts = 30
    )
    
    Write-Info "Waiting for $ServiceName to be healthy..."
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        $status = docker-compose -f $ComposeFile ps $ServiceName 2>$null
        if ($status -match "healthy|Up") {
            Write-Success "$ServiceName is ready"
            return $true
        }
        
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }
    
    Write-ErrorMsg "$ServiceName failed to become healthy within $($MaxAttempts * 2) seconds"
    return $false
}

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-ErrorMsg "Docker is not installed"
        exit 1
    }
    
    # Check Docker Compose
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-ErrorMsg "Docker Compose is not installed"
        exit 1
    }
    
    # Check Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-ErrorMsg "Python 3 is not installed"
        exit 1
    }
    
    # Check pytest
    try {
        python -c "import pytest" 2>$null
    } catch {
        Write-Warning "pytest not installed, installing..."
        pip install pytest pytest-asyncio
    }
    
    Write-Success "All prerequisites satisfied"
}

function Clear-Services {
    Write-Info "Cleaning up existing services..."
    docker-compose -f $ComposeFile down -v 2>$null
    Write-Success "Cleanup complete"
}

function Start-Services {
    Write-Info "Starting services..."
    
    # Start Redis
    Write-Info "Starting Redis..."
    docker-compose -f $ComposeFile up -d redis
    if (-not (Wait-ForService "redis")) {
        return $false
    }
    
    # Start Backend
    Write-Info "Starting Go Backend..."
    docker-compose -f $ComposeFile up -d backend
    if (-not (Wait-ForService "backend")) {
        return $false
    }
    
    # Start Worker
    Write-Info "Starting Python Worker..."
    docker-compose -f $ComposeFile up -d worker
    Start-Sleep -Seconds 5
    
    Write-Success "All services started"
    return $true
}

function Show-ServiceStatus {
    Write-Info "Service status:"
    docker-compose -f $ComposeFile ps
}

function Invoke-Tests {
    Write-Info "Running integration tests..."
    
    Push-Location $ProjectDir
    
    if ($Verbose) {
        python -m pytest $TestFile -v -s --tb=short
    } else {
        python -m pytest $TestFile -v
    }
    
    $testResult = $LASTEXITCODE
    Pop-Location
    
    if ($testResult -eq 0) {
        $script:TestsPassed = $true
        Write-Success "All tests passed!"
        return $true
    } else {
        Write-ErrorMsg "Some tests failed"
        return $false
    }
}

function Show-Logs {
    Write-Info "Recent logs from services:"
    
    Write-Host "`n=== Redis Logs ===" -ForegroundColor Cyan
    docker-compose -f $ComposeFile logs --tail=20 redis
    
    Write-Host "`n=== Backend Logs ===" -ForegroundColor Cyan
    docker-compose -f $ComposeFile logs --tail=20 backend
    
    Write-Host "`n=== Worker Logs ===" -ForegroundColor Cyan
    docker-compose -f $ComposeFile logs --tail=20 worker
}

function Stop-Services {
    if ($KeepAlive) {
        Write-Info "Keeping services alive (-KeepAlive flag set)"
        Write-Info "To stop services manually, run: docker-compose -f $ComposeFile down"
    } else {
        Write-Info "Tearing down services..."
        docker-compose -f $ComposeFile down -v
        Write-Success "Services stopped"
    }
}

function Show-Summary {
    Write-Host "`n=========================================" -ForegroundColor White
    Write-Host "  Integration Test Summary" -ForegroundColor White
    Write-Host "=========================================" -ForegroundColor White
    
    if ($TestsPassed) {
        Write-Success "Status: PASSED ✓"
    } else {
        Write-ErrorMsg "Status: FAILED ✗"
    }
    
    Write-Host "`nServices:"
    docker-compose -f $ComposeFile ps 2>$null
    
    if ($KeepAlive) {
        Write-Host "`nServices are still running."
        Write-Host "Access points:"
        Write-Host "  - Backend API: http://localhost:8080"
        Write-Host "  - Redis: localhost:6379"
        Write-Host "`nTo stop: docker-compose -f $ComposeFile down"
    }
    Write-Host "=========================================" -ForegroundColor White
}

# Main execution
function Main {
    Write-Host "=========================================" -ForegroundColor White
    Write-Host "  Botrix Integration Test Runner" -ForegroundColor White
    Write-Host "=========================================" -ForegroundColor White
    Write-Host ""
    
    Test-Prerequisites
    Clear-Services
    
    # Start services
    if (-not (Start-Services)) {
        Write-ErrorMsg "Failed to start services"
        Show-Logs
        exit 1
    }
    
    # Show status
    Show-ServiceStatus
    
    # Run tests
    Write-Host ""
    if (Invoke-Tests) {
        $script:TestsPassed = $true
    } else {
        $script:TestsPassed = $false
        Show-Logs
    }
    
    # Summary
    Show-Summary
    
    # Cleanup
    if (-not $KeepAlive) {
        Stop-Services
    }
    
    # Exit code
    if ($TestsPassed) {
        exit 0
    } else {
        exit 1
    }
}

# Run main
try {
    Main
} finally {
    if (-not $KeepAlive) {
        Write-Info "Cleaning up..."
        Stop-Services
    }
}
