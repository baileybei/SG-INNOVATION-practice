.PHONY: install test coverage lint clean run help

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Create venv and install dependencies
	python3 -m venv $(VENV)
	$(PIP) install -q -r requirements.txt
	@echo "✓ Dependencies installed. Activate with: source $(VENV)/bin/activate"

test:  ## Run all tests
	$(PYTEST) tests/ -q

coverage:  ## Run tests with coverage report
	$(PYTEST) tests/ --cov=src --cov-report=term-missing -q

coverage-html:  ## Generate HTML coverage report
	$(PYTEST) tests/ --cov=src --cov-report=html -q
	@echo "✓ HTML report at htmlcov/index.html"

lint:  ## Run ruff linter (install separately: pip install ruff)
	$(VENV)/bin/ruff check src/ tests/ || echo "Install ruff: pip install ruff"

run:  ## Analyze image with mock (usage: make run IMG=path/to/image.jpg)
	$(PYTHON) -m src.vision_agent $(IMG) --provider mock

run-gemini:  ## Analyze image with Gemini VLM (usage: make run-gemini IMG=path/to/image.jpg)
	$(PYTHON) -m src.vision_agent $(IMG) --provider gemini

run-json:  ## Analyze image, output JSON (usage: make run-json IMG=path/to/image.jpg PROVIDER=gemini)
	$(PYTHON) -m src.vision_agent $(IMG) --provider $(or $(PROVIDER),mock) --json

clean:  ## Remove venv, cache, and coverage artifacts
	rm -rf $(VENV) __pycache__ .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleaned"
