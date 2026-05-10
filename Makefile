.POSIX:
MAKEFLAGS += --warn-undefined-variables
.PHONY: bootstrap test fmt lint migrate compose-hub compose-vault secrets-decrypt

bootstrap:
	@echo "=== bootstrap: uv sync + pre-commit hooks ==="
	uv sync --extra dev
	uv run pre-commit install --hook-type pre-commit --hook-type prepare-commit-msg

test:
	@echo "=== test: pytest (excludes compose_* Docker markers) ==="
	uv run pytest tests -q -m "not compose_hub and not compose_vault and not compose_observability and not compose_litestream and not alembic_isolation"

fmt:
	@echo "=== fmt: ruff format (api + ti_hub + models + tests) ==="
	uv run ruff format app/backend/api app/backend/ti_hub app/backend/models tests

lint:
	@echo "=== lint: ruff check (api + ti_hub + models + tests) ==="
	uv run ruff check app/backend/api app/backend/ti_hub app/backend/models tests

migrate:
	@echo "=== migrate: alembic upgrade head (set TI_HUB_ALEMBIC_URL=sqlite+aiosqlite:///path/hub.sqlite) ==="
	uv run alembic -c app/backend/ti_hub/db/alembic.ini upgrade head

secrets-decrypt:
	@echo "=== secrets-decrypt → secrets/hub.env (needs sops + SOPS_AGE_KEY_FILE) ==="
	sops decrypt secrets/hub.sops.yaml > secrets/hub.env

compose-hub:
	@echo "=== compose-hub: minimal + quick tunnel (:8080) ==="
	docker compose -f deploy/compose/hub.yml -f deploy/compose/hub.override.dev.yml -f deploy/compose/hub.override.quicktunnel.yml --profile minimal up -d --build

compose-vault:
	@echo "=== compose-vault: minimal + quick tunnel (:8081) ==="
	docker compose -f deploy/compose/vault.yml -f deploy/compose/vault.override.dev.yml -f deploy/compose/vault.override.quicktunnel.yml --profile minimal up -d --build
