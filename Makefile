# Makefile for LAS Validator Docker operations

.PHONY: help build run stop clean dev dev-stop logs shell rebuild

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the production Docker image
	docker-compose build

run: ## Run the production container
	docker-compose up -d

stop: ## Stop the production container
	docker-compose down

clean: ## Remove containers, networks, and volumes
	docker-compose down -v
	docker system prune -f

dev: ## Run the development container with hot-reloading
	docker-compose -f docker-compose.dev.yml up

dev-stop: ## Stop the development container
	docker-compose -f docker-compose.dev.yml down

logs: ## Show container logs
	docker-compose logs -f

shell: ## Open a shell in the running container
	docker exec -it las-validator-app /bin/bash

rebuild: ## Rebuild and run the production container
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

dev-rebuild: ## Rebuild and run the development container
	docker-compose -f docker-compose.dev.yml down
	docker-compose -f docker-compose.dev.yml build --no-cache
	docker-compose -f docker-compose.dev.yml up

test: ## Run tests inside the container (if tests exist)
	docker exec -it las-validator-app python -m pytest

port-check: ## Check if port 5000 is already in use
	@echo "Checking port 5000..."
	@lsof -i :5000 || echo "Port 5000 is free"