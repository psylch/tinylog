.PHONY: dev test lint build fmt clean docker help

dev:  ## Start backend + frontend dev servers
	@echo "Starting backend on :7892..."
	uv run tinylog serve --port 7892 &
	@echo "Starting frontend..."
	cd frontend && npm run dev

test:  ## Run all tests
	uv run pytest tests/ -v
	cd frontend && npm run lint && npm run build

lint:  ## Run linters
	uv run ruff check .
	cd frontend && npm run lint

build:  ## Build frontend for production
	cd frontend && npm run build

fmt:  ## Format code
	uv run ruff check . --fix
	uv run ruff format .

clean:  ## Clean build artifacts
	rm -rf frontend/dist .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker:  ## Build Docker image
	docker build -t tinylog .

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
