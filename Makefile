.POSIX:
MAKEFLAGS += --warn-undefined-variables
.PHONY: bootstrap test fmt lint compose-hub compose-vault

bootstrap:
	@echo "=== bootstrap: uv sync (dev extras) ==="
	uv sync --extra dev

test:
	@echo "=== test: pytest via uv ==="
	uv run pytest tests -q

fmt:
	@echo "=== fmt: ruff format (hub + tests) ==="
	uv run ruff format app/backend/ti_hub tests

lint:
	@echo "=== lint: ruff check (hub + tests) ==="
	uv run ruff check app/backend/ti_hub tests

compose-hub:
	@echo "=== compose-hub: deploy/compose/hub.yml arrives in M0.3 ==="

compose-vault:
	@echo "=== compose-vault: vault compose arrives in M0.4 ==="
