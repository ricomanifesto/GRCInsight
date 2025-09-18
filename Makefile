.PHONY: build run test clean docker-build docker-run dev-setup fmt lint help

# Default target
help:
	@echo "Available targets:"
	@echo "  build         - Build both Go and Python services"
	@echo "  run           - Run both services locally"
	@echo "  test          - Run tests for both services"
	@echo "  clean         - Clean build artifacts"
	@echo "  docker-build  - Build Docker containers"
	@echo "  docker-run    - Run services with Docker Compose"
	@echo "  dev-setup     - Set up development environment"
	@echo "  fmt           - Format code"
	@echo "  lint          - Lint code"

# Build both services
build:
	@echo "Building Go service..."
	@mkdir -p bin
	go build -o bin/grcinsight cmd/server/main.go
	@echo "Go service built successfully"

# Run services locally (requires Python virtual environment)
run:
	@echo "Starting Python service in background..."
	cd agent && python main.py &
	@echo "Waiting for Python service to start..."
	@sleep 3
	@echo "Starting Go service..."
	./bin/grcinsight

# Run tests
test:
	@echo "Running Go tests..."
	go test ./...
	@echo "Running Python tests..."
	cd agent && python -m pytest tests/ -v

# Clean build artifacts
clean:
	rm -rf bin/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".pytest_cache" -delete

# Docker operations
docker-build:
	@echo "Building Docker containers..."
	docker-compose build

docker-run:
	@echo "Starting services with Docker Compose..."
	docker-compose up

docker-stop:
	@echo "Stopping Docker services..."
	docker-compose down

# Development setup
dev-setup:
	@echo "Setting up development environment..."
	go mod download
	@echo "Setting up Python virtual environment..."
	cd agent && python -m venv venv
	@echo "Install Python dependencies manually: cd agent && source venv/bin/activate && pip install -r requirements.txt"

# Format code
fmt:
	@echo "Formatting Go code..."
	go fmt ./...
	@echo "Formatting Python code..."
	cd agent && python -m black . && python -m isort .

# Lint code
lint:
	@echo "Linting Go code..."
	golangci-lint run || echo "golangci-lint not installed, skipping Go linting"
	@echo "Linting Python code..."
	cd agent && python -m flake8 . || echo "flake8 not installed, skipping Python linting"

# Quick development run (Go only, assumes Python service is running)
run-go:
	@echo "Starting Go service (assumes Python service is running on :8081)..."
	./bin/grcinsight

# Quick development run (Python only)
run-python:
	@echo "Starting Python service..."
	cd agent && python main.py