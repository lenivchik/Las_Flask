# LAS Validator Docker Management (Poetry Edition)

.PHONY: build run stop clean logs shell test help dev poetry-install

# Default target
help:
	@echo "LAS Validator Docker Commands (Poetry Edition):"
	@echo ""
	@echo "  build          - Build the Docker image"
	@echo "  run            - Run the application with docker-compose"
	@echo "  run-simple     - Run only the Flask app (without nginx)"
	@echo "  dev            - Run in development mode with hot reload"
	@echo "  stop           - Stop all containers"
	@echo "  clean          - Stop containers and remove images"
	@echo "  logs           - Show application logs"
	@echo "  logs-nginx     - Show nginx logs"
	@echo "  shell          - Open shell in the app container"
	@echo "  test           - Run health check test"
	@echo "  rebuild        - Stop, clean, and rebuild everything"
	@echo "  poetry-install - Install dependencies with Poetry locally"
	@echo "  poetry-update  - Update Poetry dependencies"

# Build the Docker image
build:
	@echo "Building LAS Validator Docker image..."
	docker-compose build

# Run the full application stack
run:
	@echo "Starting LAS Validator application..."
	docker-compose up -d
	@echo "Application started! Access it at:"
	@echo "  - HTTP: http://localhost"
	@echo "  - Direct Flask: http://localhost:5000"

# Run only the Flask application (without nginx)
run-simple:
	@echo "Starting Flask application only..."
	docker-compose up -d las-validator
	@echo "Flask application started at http://localhost:5000"

# Stop all containers
stop:
	@echo "Stopping LAS Validator containers..."
	docker-compose down

# Clean up containers and images
clean:
	@echo "Cleaning up containers and images..."
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f

# Show application logs
logs:
	docker-compose logs -f las-validator

# Show nginx logs
logs-nginx:
	docker-compose logs -f nginx

# Open shell in the application container
shell:
	docker-compose exec las-validator /bin/bash

# Test the application
test:
	@echo "Testing application health..."
	@curl -f http://localhost:5000/api/health || echo "Application not responding"
	@curl -f http://localhost/ || echo "Nginx not responding"

# Rebuild everything from scratch
rebuild: stop clean build run
	@echo "Rebuild complete!"

# Development mode (with file watching and local lascheck)
dev:
	@echo "Starting in development mode with Poetry..."
	@echo "Make sure you have the lascheck directory with your local package"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Install Poetry dependencies locally
poetry-install:
	@echo "Installing dependencies with Poetry..."
	poetry install

# Update Poetry dependencies
poetry-update:
	@echo "Updating Poetry dependencies..."
	poetry update

# Run Poetry shell
poetry-shell:
	@echo "Starting Poetry shell..."
	poetry shell

# Lock Poetry dependencies
poetry-lock:
	@echo "Locking Poetry dependencies..."
	poetry lock

# Production deployment
deploy:
	@echo "Deploying to production..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# View container status
status:
	docker-compose ps

# Update images
update:
	docker-compose pull
	docker-compose up -d --build