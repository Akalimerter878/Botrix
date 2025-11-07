# Test runner script for PowerShell
# Runs pytest with coverage reporting

Write-Host "================================" -ForegroundColor Cyan
Write-Host "   Botrix Test Suite Runner" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if pytest is installed
Write-Host "Checking for pytest..." -ForegroundColor Yellow
python -m pytest --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pytest not found. Installing dependencies..." -ForegroundColor Red
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install dependencies. Exiting." -ForegroundColor Red
        exit 1
    }
}

Write-Host "pytest found!" -ForegroundColor Green
Write-Host ""

# Parse command line arguments
$TestType = $args[0]
$Coverage = $args -contains "--coverage" -or $args -contains "-c"
$Verbose = $args -contains "--verbose" -or $args -contains "-v"

# Build pytest command
$PytestArgs = @()

# Determine test selection
switch ($TestType) {
    "unit" {
        Write-Host "Running UNIT tests only..." -ForegroundColor Cyan
        $PytestArgs += "-m", "unit"
    }
    "integration" {
        Write-Host "Running INTEGRATION tests only..." -ForegroundColor Cyan
        $PytestArgs += "-m", "integration"
    }
    "kasada" {
        Write-Host "Running KASADA tests only..." -ForegroundColor Cyan
        $PytestArgs += "tests/test_kasada.py"
    }
    "email" {
        Write-Host "Running EMAIL tests only..." -ForegroundColor Cyan
        $PytestArgs += "tests/test_email.py"
    }
    "account" {
        Write-Host "Running ACCOUNT CREATOR tests only..." -ForegroundColor Cyan
        $PytestArgs += "tests/test_account_creator.py"
    }
    default {
        Write-Host "Running ALL tests..." -ForegroundColor Cyan
        $PytestArgs += "tests/"
    }
}

# Add coverage if requested
if ($Coverage) {
    Write-Host "Coverage reporting ENABLED" -ForegroundColor Green
    $PytestArgs += "--cov=workers"
    $PytestArgs += "--cov-report=html"
    $PytestArgs += "--cov-report=term-missing"
} else {
    Write-Host "Coverage reporting disabled (use --coverage to enable)" -ForegroundColor Yellow
}

# Add verbose if requested
if ($Verbose) {
    $PytestArgs += "-v"
}

# Add color output
$PytestArgs += "--color=yes"

# Add asyncio mode
$PytestArgs += "--asyncio-mode=auto"

Write-Host ""
Write-Host "Executing: python -m pytest $($PytestArgs -join ' ')" -ForegroundColor Gray
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Run pytest
python -m pytest @PytestArgs

# Check exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "   ✓ All tests passed!" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Cyan
    
    if ($Coverage) {
        Write-Host ""
        Write-Host "Coverage report generated in htmlcov/index.html" -ForegroundColor Cyan
    }
} else {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "   ✗ Some tests failed" -ForegroundColor Red
    Write-Host "================================" -ForegroundColor Cyan
    exit 1
}
