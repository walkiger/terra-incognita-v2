.POSIX:
MAKEFLAGS += --warn-undefined-variables
.PHONY: bootstrap test fmt lint compose-hub compose-vault

bootstrap:
	@echo "=== bootstrap: uv sync (dev extras) ==="
	uv sync --extra dev

test:
	@echo "=== test: pytest via uv (excludes compose_* integration markers) ==="
	uv run pytest tests -q -m "not compose_hub and not compose_vault"

fmt:
	@echo "=== fmt: ruff format (hub API stub + ti_hub + tests) ==="
	uv run ruff format deploy/api/app app/backend/ti_hub tests

lint:
	@echo "=== lint: ruff check (hub API stub + ti_hub + tests) ==="
	uv run ruff check deploy/api/app app/backend/ti_hub tests

compose-hub:
	@echo "=== compose-hub: minimal profile (quick tunnel; host :8080 in override.dev) ==="
	docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.dev.yml --profile minimal up -d --build

compose-vault:
	@echo "=== compose-vault: minimal profile (host :8081 in override.dev) ==="
	docker compose -f deploy/compose/vault.yml -f deploy/compose/vault.override.dev.yml --profile minimal up -d --build
