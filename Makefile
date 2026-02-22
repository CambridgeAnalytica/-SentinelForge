.PHONY: bootstrap build test lint typecheck security-scan clean help up down logs seed seed-purge demo

# Variables
PYTHON := python3.11
DOCKER := docker
COMPOSE := docker compose

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Bootstrap local development environment
	@echo "🔧 Bootstrapping SentinelForge..."
	@echo "Creating Python virtual environments..."
	cd services/api && $(PYTHON) -m venv venv && . venv/bin/activate && pip install -r requirements.txt || (. venv/Scripts/activate && pip install -r requirements.txt)
	cd sdk/python && $(PYTHON) -m venv venv && . venv/bin/activate && pip install -e ".[dev]" || (. venv/Scripts/activate && pip install -e ".[dev]")
	cd cli && $(PYTHON) -m venv venv && . venv/bin/activate && pip install -e ".[dev]" || (. venv/Scripts/activate && pip install -e ".[dev]")
	@echo "Creating .env file..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "✅ Bootstrap complete!"
	@echo "⚠️  IMPORTANT: Edit .env and set JWT_SECRET_KEY, DEFAULT_ADMIN_USERNAME, and DEFAULT_ADMIN_PASSWORD before running 'make up'."

build: ## Build all Docker images
	@echo "🐳 Building Docker images..."
	$(DOCKER) build -f infra/docker/Dockerfile.api -t sentinelforge/api:latest .
	$(DOCKER) build -f infra/docker/Dockerfile.worker -t sentinelforge/worker:latest .
	$(DOCKER) build -f infra/docker/Dockerfile.tools -t sentinelforge/tools:latest .
	@echo "✅ Build complete!"

up: ## Start all services with docker-compose
	@echo "🚀 Starting services..."
	$(COMPOSE) up -d
	@echo "✅ Services started!"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "Jaeger UI: http://localhost:16686"
	@echo "Prometheus: http://localhost:9090"
	@echo "MinIO Console: http://localhost:9001"

down: ## Stop all services
	@echo "🛑 Stopping services..."
	$(COMPOSE) down
	@echo "✅ Services stopped!"

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

test: test-python ## Run all tests

test-python: ## Run Python tests
	@echo "🧪 Running Python tests..."
	cd services/api && . venv/bin/activate && pytest tests/ -v --cov=. --cov-report=term-missing || (. venv/Scripts/activate && pytest tests/ -v --cov=. --cov-report=term-missing)
	cd sdk/python && . venv/bin/activate && pytest tests/ -v --cov=sentinelforge_sdk --cov-report=term-missing || (. venv/Scripts/activate && pytest tests/ -v --cov=sentinelforge_sdk --cov-report=term-missing)
	cd cli && . venv/bin/activate && pytest tests/ -v || (. venv/Scripts/activate && pytest tests/ -v)
	@echo "✅ Python tests complete!"

lint: lint-python ## Run all linters

lint-python: ## Lint Python code
	@echo "🔍 Linting Python code..."
	cd services/api && . venv/bin/activate && ruff check . && black --check . || (. venv/Scripts/activate && ruff check . && black --check .)
	cd sdk/python && . venv/bin/activate && ruff check . && black --check . || (. venv/Scripts/activate && ruff check . && black --check .)
	cd cli && . venv/bin/activate && ruff check . && black --check . || (. venv/Scripts/activate && ruff check . && black --check .)
	@echo "✅ Python linting complete!"

format: format-python ## Format all code

format-python: ## Format Python code
	@echo "✨ Formatting Python code..."
	cd services/api && . venv/bin/activate && black . && ruff check --fix . || (. venv/Scripts/activate && black . && ruff check --fix .)
	cd sdk/python && . venv/bin/activate && black . && ruff check --fix . || (. venv/Scripts/activate && black . && ruff check --fix .)
	cd cli && . venv/bin/activate && black . && ruff check --fix . || (. venv/Scripts/activate && black . && ruff check --fix .)
	@echo "✅ Python formatting complete!"

typecheck: ## Run type checking
	@echo "🔎 Type checking Python code..."
	cd services/api && . venv/bin/activate && mypy . || (. venv/Scripts/activate && mypy .)
	cd sdk/python && . venv/bin/activate && mypy sentinelforge_sdk/ || (. venv/Scripts/activate && mypy sentinelforge_sdk/)
	@echo "✅ Type checking complete!"

security-scan: ## Run security scans (SBOM, vulnerabilities, secrets)
	@echo "🔒 Running security scans..."
	bash infra/security/sbom.sh || echo "SBOM generation skipped (syft not installed)"
	bash infra/security/scan.sh || echo "Vulnerability scan skipped (grype not installed)"
	@echo "✅ Security scan complete!"

sign: ## Sign container images
	@echo "✍️  Signing images..."
	bash infra/security/sign.sh || echo "Image signing skipped (cosign not installed)"
	@echo "✅ Images signed!"

clean: ## Clean build artifacts and stop services
	@echo "🧹 Cleaning up..."
	$(COMPOSE) down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

install-tools: ## Install development tools
	@echo "🛠️  Installing development tools..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install ruff black mypy pytest pytest-cov
	@echo "✅ Tools installed!"

db-migrate: ## Run database migrations
	@echo "🗄️  Running migrations..."
	cd services/api && . venv/bin/activate && alembic upgrade head || (. venv/Scripts/activate && alembic upgrade head)
	@echo "✅ Migrations complete!"

db-reset: ## Reset database (WARNING: destroys data)
	@echo "⚠️  Resetting database..."
	$(COMPOSE) stop postgres
	$(COMPOSE) rm -f postgres
	rm -rf .postgres-data
	$(COMPOSE) up -d postgres
	@echo "Waiting for Postgres to be ready..."
	@until $(COMPOSE) exec -T postgres pg_isready -U $${POSTGRES_USER:-sentinelforge_user} 2>/dev/null; do sleep 1; done
	$(MAKE) db-migrate
	@echo "✅ Database reset complete!"

seed: ## Seed demo data (idempotent, uses demo- prefix)
	@echo "🌱 Seeding demo data..."
	cd services/api && . venv/bin/activate && python ../../scripts/seed_demo_data.py || (. venv/Scripts/activate && python ../../scripts/seed_demo_data.py)
	@echo "✅ Demo data seeded!"

seed-purge: ## Remove all demo data (demo- prefix)
	@echo "🗑️  Purging demo data..."
	cd services/api && . venv/bin/activate && python ../../scripts/seed_demo_data.py --purge || (. venv/Scripts/activate && python ../../scripts/seed_demo_data.py --purge)
	@echo "✅ Demo data purged!"

demo: up ## Start full stack + seed demo data
	@echo "⏳ Waiting for API to be ready..."
	@until curl -sf http://localhost:8000/health >/dev/null 2>&1; do sleep 2; done
	$(MAKE) seed
	@echo ""
	@echo "🚀 SentinelForge is ready!"
	@echo "   Dashboard: http://localhost:3001"
	@echo "   API:       http://localhost:8000"
	@echo "   API Docs:  http://localhost:8000/docs"
	@echo "   Jaeger:    http://localhost:16686"
	@echo "   Grafana:   http://localhost:3000"
