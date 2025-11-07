#!/bin/bash
#
# Integration Test Runner for Botrix
#
# This script:
# 1. Starts all required services (Redis, Backend, Worker)
# 2. Waits for services to be healthy
# 3. Runs integration tests
# 4. Tears down services
# 5. Reports results
#
# Usage:
#   ./scripts/run_integration_tests.sh [--keep-alive] [--verbose]
#
# Options:
#   --keep-alive    Don't tear down services after tests
#   --verbose       Show detailed output
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
TEST_COMPOSE_FILE="$PROJECT_DIR/docker-compose.test.yml"
TEST_FILE="$PROJECT_DIR/tests/test_full_flow.py"

KEEP_ALIVE=false
VERBOSE=false
TESTS_PASSED=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --keep-alive)
            KEEP_ALIVE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    log_info "Waiting for $service to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" ps | grep "$service" | grep -q "healthy\|Up"; then
            log_success "$service is ready"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "$service failed to become healthy within $((max_attempts * 2)) seconds"
    return 1
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check pytest
    if ! python3 -c "import pytest" 2>/dev/null; then
        log_warning "pytest not installed, installing..."
        pip install pytest pytest-asyncio
    fi
    
    log_success "All prerequisites satisfied"
}

cleanup_services() {
    log_info "Cleaning up existing services..."
    docker-compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    log_success "Cleanup complete"
}

start_services() {
    log_info "Starting services..."
    
    # Start Redis
    log_info "Starting Redis..."
    docker-compose -f "$COMPOSE_FILE" up -d redis
    wait_for_service "redis"
    
    # Start Backend
    log_info "Starting Go Backend..."
    docker-compose -f "$COMPOSE_FILE" up -d backend
    wait_for_service "backend"
    
    # Start Worker
    log_info "Starting Python Worker..."
    docker-compose -f "$COMPOSE_FILE" up -d worker
    sleep 5  # Give worker time to initialize
    
    log_success "All services started"
}

show_service_status() {
    log_info "Service status:"
    docker-compose -f "$COMPOSE_FILE" ps
}

run_tests() {
    log_info "Running integration tests..."
    
    cd "$PROJECT_DIR"
    
    if [ "$VERBOSE" = true ]; then
        python3 -m pytest "$TEST_FILE" -v -s --tb=short
    else
        python3 -m pytest "$TEST_FILE" -v
    fi
    
    if [ $? -eq 0 ]; then
        TESTS_PASSED=true
        log_success "All tests passed!"
        return 0
    else
        log_error "Some tests failed"
        return 1
    fi
}

show_logs() {
    log_info "Recent logs from services:"
    
    echo ""
    echo "=== Redis Logs ==="
    docker-compose -f "$COMPOSE_FILE" logs --tail=20 redis
    
    echo ""
    echo "=== Backend Logs ==="
    docker-compose -f "$COMPOSE_FILE" logs --tail=20 backend
    
    echo ""
    echo "=== Worker Logs ==="
    docker-compose -f "$COMPOSE_FILE" logs --tail=20 worker
}

teardown_services() {
    if [ "$KEEP_ALIVE" = true ]; then
        log_info "Keeping services alive (--keep-alive flag set)"
        log_info "To stop services manually, run: docker-compose -f $COMPOSE_FILE down"
    else
        log_info "Tearing down services..."
        docker-compose -f "$COMPOSE_FILE" down -v
        log_success "Services stopped"
    fi
}

print_summary() {
    echo ""
    echo "========================================="
    echo "  Integration Test Summary"
    echo "========================================="
    
    if [ "$TESTS_PASSED" = true ]; then
        log_success "Status: PASSED ✓"
    else
        log_error "Status: FAILED ✗"
    fi
    
    echo ""
    echo "Services:"
    docker-compose -f "$COMPOSE_FILE" ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Services stopped"
    
    echo ""
    if [ "$KEEP_ALIVE" = true ]; then
        echo "Services are still running."
        echo "Access points:"
        echo "  - Backend API: http://localhost:8080"
        echo "  - Redis: localhost:6379"
        echo ""
        echo "To stop: docker-compose -f $COMPOSE_FILE down"
    fi
    echo "========================================="
}

# Trap Ctrl+C
trap cleanup_on_exit INT TERM EXIT

cleanup_on_exit() {
    if [ "$KEEP_ALIVE" = false ]; then
        log_info "Cleaning up..."
        teardown_services
    fi
}

# Main execution
main() {
    echo "========================================="
    echo "  Botrix Integration Test Runner"
    echo "========================================="
    echo ""
    
    check_prerequisites
    cleanup_services
    
    # Start services
    if ! start_services; then
        log_error "Failed to start services"
        show_logs
        exit 1
    fi
    
    # Show status
    show_service_status
    
    # Run tests
    echo ""
    if run_tests; then
        TESTS_PASSED=true
    else
        TESTS_PASSED=false
        show_logs
    fi
    
    # Summary
    print_summary
    
    # Cleanup
    if [ "$KEEP_ALIVE" = false ]; then
        teardown_services
    fi
    
    # Exit code
    if [ "$TESTS_PASSED" = true ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main
