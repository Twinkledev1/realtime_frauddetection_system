.PHONY: help install test lint format clean setup start stop deploy

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install all dependencies"
	@echo "  test       - Run all tests"
	@echo "  lint       - Run linting checks"
	@echo "  format     - Format code with black and isort"
	@echo "  clean      - Clean up temporary files"
	@echo "  setup      - Initial project setup"
	@echo "  start      - Start development environment"
	@echo "  stop       - Stop development environment"
	@echo "  deploy     - Deploy to production"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v --cov=src --cov-report=html

# Run linting
lint:
	@echo "Running linting checks..."
	flake8 src/ tests/
	mypy src/
	bandit -r src/

# Format code
format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ htmlcov/ .coverage

# Initial setup
setup: install
	@echo "Setting up project..."
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	docker-compose up -d

# Start development environment
start:
	@echo "Starting development environment..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Services started:"
	@echo "  - Kafka: localhost:9092"
	@echo "  - Kafka UI: http://localhost:8080"
	@echo "  - Redis: localhost:6379"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3000 (admin/admin)"

# Stop development environment
stop:
	@echo "Stopping development environment..."
	docker-compose down
	@echo "All services stopped"

# Deploy to production
deploy:
	@echo "Deploying to production..."
	@echo "This would deploy to your production environment"
	@echo "Please implement your deployment strategy"

# Run specific components
run-simulator:
	@echo "Starting transaction simulator..."
	PYTHONPATH=. venv/bin/python src/transaction_simulator/main.py

run-spark:
	@echo "Starting Spark Streaming job..."
	PYTHONPATH=. venv/bin/python src/spark_streaming/fraud_detection_job.py

run-api:
	@echo "Starting API server..."
	PYTHONPATH=. venv/bin/python src/api/main.py

# Test with infrastructure
test-with-infra:
	@echo "Testing with infrastructure..."
	@echo "1. Starting infrastructure..."
	@make start
	@echo "2. Waiting for Kafka to be ready..."
	@sleep 30
	@echo "3. Running comprehensive test..."
	PYTHONPATH=. venv/bin/python scripts/test_phase1.py
	@echo "4. Infrastructure is running. Use 'make stop' to stop it."

# Check infrastructure status
status:
	@echo "Checking infrastructure status..."
	docker-compose ps

# Development helpers
dev-install: install
	@echo "Installing development dependencies..."
	pre-commit install

dev-test: format lint test
	@echo "Development checks completed"

# Database operations
db-migrate:
	@echo "Running database migrations..."
	@echo "Implement your migration strategy"

db-seed:
	@echo "Seeding database with sample data..."
	@echo "Implement your seeding strategy"

# Monitoring
monitor:
	@echo "Starting monitoring stack..."
	docker-compose -f docker-compose.monitoring.yml up -d

# Performance testing
perf-test:
	@echo "Running performance tests..."
	locust -f tests/performance/locustfile.py

# Phase testing
test-phase1:
	@echo "Testing Phase 1: Foundation & Infrastructure"
	PYTHONPATH=. venv/bin/python scripts/test_phase1.py

test-phase2:
	@echo "Testing Phase 2: Core Streaming Pipeline"
	PYTHONPATH=. venv/bin/python scripts/test_phase2.py

test-phase3:
	@echo "Testing Phase 3: Data Storage & Analytics"
	PYTHONPATH=. venv/bin/python scripts/test_phase3.py

test-phase4:
	@echo "Testing Phase 4: Monitoring & Visualization"
	PYTHONPATH=. venv/bin/python scripts/test_phase4.py

test-fixes:
	@echo "Testing Phase 3 Fixes"
	PYTHONPATH=. venv/bin/python scripts/test_fixes.py

# Monitoring
start-monitoring:
	@echo "Starting Monitoring Dashboard"
	PYTHONPATH=. venv/bin/python src/monitoring/main.py

monitoring-health-check:
	@echo "Running Monitoring Health Check"
	PYTHONPATH=. venv/bin/python src/monitoring/main.py --mode health-check

# Phase 5: Production Readiness
test-phase5:
	@echo "Testing Phase 5: Production Readiness & Optimization"
	PYTHONPATH=. venv/bin/python scripts/test_phase5.py

load-test:
	@echo "Running Load Tests"
	PYTHONPATH=. venv/bin/python -c "from src.testing.load_testing import run_quick_load_test; result = run_quick_load_test(); print(f'Load Test Complete: {result.requests_per_second:.2f} req/s')"

stress-test:
	@echo "Running Stress Tests"
	PYTHONPATH=. venv/bin/python -c "from src.testing.load_testing import run_stress_test; result = run_stress_test(); print(f'Stress Test Complete: {result.requests_per_second:.2f} req/s')"

build-docker:
	@echo "Building Docker Image"
	docker build -t fraud-detection-system .

run-docker:
	@echo "Running Docker Container"
	docker run -p 8080:8080 fraud-detection-system

# Documentation
docs:
	@echo "Building documentation..."
	mkdocs build

docs-serve:
	@echo "Serving documentation..."
	mkdocs serve
