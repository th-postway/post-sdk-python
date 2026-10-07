.PHONY: check format lint typecheck test test-integration demo build clean

check: ## format:check + lint + typecheck + unit tests. Run before every commit.
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .

typecheck:
	uv run mypy

test:
	uv run pytest

test-integration: ## read-only live tests; skipped without POSTWAY_MERCHANT_BASE_URL and POSTWAY_MERCHANT_ACCESS_TOKEN
	uv run pytest -m integration tests/integration

demo: ## runnable Quick start; read-only, sandbox by default (see demo/README.md)
	uv run python demo/quick_start.py

build: clean
	uv build

clean:
	rm -rf dist
