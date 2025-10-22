.PHONY: help setup start stop restart clean test lint format

# Colors for output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
NC     := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Java Unit Test Agent - Make Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# ============ Setup ============

setup: ## Initial setup (install dependencies, create .env)
	@echo "$(GREEN)Setting up Java Unit Test Agent...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)Created .env file. Please edit it with your API keys!$(NC)"; \
	fi
	@echo "$(GREEN)Installing Python dependencies...$(NC)"
	cd python && pip install -r requirements.txt
	@echo "$(GREEN)Installing TypeScript dependencies...$(NC)"
	cd typescript && npm install
	@echo "$(GREEN)Setup complete!$(NC)"

# ============ Docker Services ============

docker-up: ## Start all Docker services
	@echo "$(GREEN)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "  - Qdrant: http://localhost:6333"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3001 (admin/admin)"

docker-down: ## Stop all Docker services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-ps: ## Show running Docker containers
	docker-compose ps

# ============ Application Services ============

start-api: ## Start Python API server
	@echo "$(GREEN)Starting Python API...$(NC)"
	cd python && uvicorn api.server:app --reload --host 0.0.0.0 --port 8000


start: docker-up ## Start all services (Docker + API)
	@echo "$(GREEN)Starting all services...$(NC)"
	@make start-api &
	@echo "$(GREEN)All services started!$(NC)"
	@echo "  - API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"

stop: docker-down ## Stop all services

restart: stop start ## Restart all services

# ============ Development ============

dev: ## Start development environment (Docker + API dev mode)
	@echo "$(GREEN)Starting development environment...$(NC)"
	@make docker-up
	@echo "$(YELLOW)Run 'make start-api' and 'make start-ui' in separate terminals$(NC)"

logs-api: ## Show API logs
	tail -f python/logs/api.log

test: ## Run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	cd python && pytest tests/ -v --cov=.

test-unit: ## Run unit tests only
	@echo "$(GREEN)Running unit tests...$(NC)"
	cd python && pytest tests/unit/ -v

test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	cd python && pytest tests/integration/ -v

lint: ## Run linters
	@echo "$(GREEN)Running linters...$(NC)"
	cd python && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	cd python && mypy . --ignore-missing-imports

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	cd python && black . --line-length 100
	cd python && isort .

# ============ Database ============

db-health: ## Check database health
	@echo "$(GREEN)Checking database health...$(NC)"
	@curl -s http://localhost:6333/health | jq '.' || echo "$(RED)Qdrant not responding$(NC)"
	@nc -zv localhost 7687 2>&1 | grep -q succeeded && echo "$(GREEN)Memgraph: OK$(NC)" || echo "$(RED)Memgraph: FAIL$(NC)"
	@redis-cli -h localhost ping 2>&1 | grep -q PONG && echo "$(GREEN)Redis: OK$(NC)" || echo "$(RED)Redis: FAIL$(NC)"

db-reset: ## Reset all databases (WARNING: deletes all data!)
	@echo "$(RED)This will delete all data! Press Ctrl+C to cancel...$(NC)"
	@sleep 3
	docker-compose down -v
	docker-compose up -d
	@echo "$(GREEN)Databases reset complete$(NC)"

# ============ Project Tools ============

index: ## Index a Java project (usage: make index PROJECT=/path/to/project)
	@if [ -z "$(PROJECT)" ]; then \
		echo "$(RED)Error: PROJECT path required$(NC)"; \
		echo "Usage: make index PROJECT=/path/to/java/project"; \
		exit 1; \
	fi
	@echo "$(GREEN)Indexing project: $(PROJECT)$(NC)"
	curl -X POST http://localhost:8000/api/index/project \
		-H "Content-Type: application/json" \
		-d '{"project_path": "$(PROJECT)"}' | jq '.'

stats: ## Show indexing statistics
	@echo "$(GREEN)Fetching statistics...$(NC)"
	curl -s http://localhost:8000/api/stats | jq '.'

health: ## Check API health
	@echo "$(GREEN)Checking API health...$(NC)"
	curl -s http://localhost:8000/health | jq '.'

# ============ Cleanup ============

clean: ## Clean temporary files
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -prune
	@echo "$(GREEN)Cleanup complete$(NC)"

clean-logs: ## Clean log files
	@echo "$(YELLOW)Cleaning logs...$(NC)"
	rm -rf python/logs/*.log
	@echo "$(GREEN)Logs cleaned$(NC)"

purge: clean docker-down ## Complete cleanup (Docker volumes + temp files)
	@echo "$(RED)Removing Docker volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)Purge complete$(NC)"

# ============ Documentation ============

docs: ## Open documentation
	@echo "$(GREEN)Opening documentation...$(NC)"
	@open docs/START_NOW.md || xdg-open docs/START_NOW.md

api-docs: ## Open API documentation
	@echo "$(GREEN)Opening API docs...$(NC)"
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs

# ============ Build ============

build-ts: ## Build TypeScript plugin
	@echo "$(GREEN)Building TypeScript plugin...$(NC)"
	cd typescript && npm run build


build: build-ts ## Build all components

# ============ Configuration ============

config-check: ## Check configuration
	@echo "$(GREEN)Checking configuration...$(NC)"
	cd python && python config.py

env-example: ## Create .env from .env.example
	@if [ -f .env ]; then \
		echo "$(YELLOW).env already exists. Backup created as .env.backup$(NC)"; \
		cp .env .env.backup; \
	fi
	cp .env.example .env
	@echo "$(GREEN).env created. Please edit with your settings!$(NC)"

# ============ Monitoring ============

monitoring: ## Open monitoring dashboards
	@echo "$(GREEN)Opening monitoring dashboards...$(NC)"
	@open http://localhost:3001 || xdg-open http://localhost:3001  # Grafana
	@open http://localhost:9090 || xdg-open http://localhost:9090  # Prometheus

# ============ Examples ============

example-simple: ## Index simple example project
	make index PROJECT=./examples/simple

example-spring: ## Index Spring Boot example
	make index PROJECT=./examples/spring-boot

# ============ Info ============

info: ## Show system information
	@echo "$(GREEN)Java Unit Test Agent - System Info$(NC)"
	@echo ""
	@echo "$(YELLOW)Environment:$(NC)"
	@python --version
	@node --version
	@npm --version
	@docker --version
	@echo ""
	@echo "$(YELLOW)Docker Services:$(NC)"
	@make docker-ps
	@echo ""
	@echo "$(YELLOW)Database Health:$(NC)"
	@make db-health

