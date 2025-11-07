# Botrix Backend Makefile

# Variables
BINARY_NAME=botrix-backend
GO=go
GOFLAGS=-v

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help: ## Show this help message
	@echo "Botrix Backend - Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Development
.PHONY: run
run: ## Run the application
	$(GO) run main.go

.PHONY: build
build: ## Build the application
	$(GO) build $(GOFLAGS) -o $(BINARY_NAME) .

.PHONY: build-prod
build-prod: ## Build optimized production binary
	$(GO) build -ldflags="-s -w" -o $(BINARY_NAME) .

# Dependencies
.PHONY: deps
deps: ## Download dependencies
	$(GO) mod download

.PHONY: deps-update
deps-update: ## Update dependencies
	$(GO) get -u ./...
	$(GO) mod tidy

.PHONY: tidy
tidy: ## Tidy go.mod
	$(GO) mod tidy

# Code quality
.PHONY: fmt
fmt: ## Format code
	$(GO) fmt ./...

.PHONY: vet
vet: ## Run go vet
	$(GO) vet ./...

.PHONY: lint
lint: ## Run golangci-lint (requires golangci-lint installed)
	golangci-lint run

# Testing
.PHONY: test
test: ## Run tests
	$(GO) test -v ./...

.PHONY: test-coverage
test-coverage: ## Run tests with coverage
	$(GO) test -v -coverprofile=coverage.out ./...
	$(GO) tool cover -html=coverage.out -o coverage.html

.PHONY: test-race
test-race: ## Run tests with race detector
	$(GO) test -race -v ./...

# Database
.PHONY: db-reset
db-reset: ## Reset database (delete botrix.db)
	rm -f botrix.db

# Clean
.PHONY: clean
clean: ## Clean build artifacts
	rm -f $(BINARY_NAME)
	rm -f coverage.out coverage.html
	rm -f botrix.db

# Development helpers
.PHONY: dev
dev: deps fmt vet run ## Format, vet, and run

.PHONY: check
check: fmt vet test ## Format, vet, and test

# Install tools
.PHONY: install-tools
install-tools: ## Install development tools
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Watch mode (requires air: go install github.com/cosmtrek/air@latest)
.PHONY: watch
watch: ## Run with hot reload (requires air)
	air

# Docker (future)
.PHONY: docker-build
docker-build: ## Build Docker image
	docker build -t botrix-backend:latest .

.PHONY: docker-run
docker-run: ## Run Docker container
	docker run -p 8080:8080 botrix-backend:latest
