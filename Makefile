.POSIX:
MAKEFLAGS += --warn-undefined-variables
.PHONY: bootstrap test fmt lint compose-hub compose-vault

bootstrap:
	@echo "=== bootstrap: dev deps — full uv toolchain lands in M0.2 ==="
	@echo "Hint (today): py -m pip install -r requirements-ci.txt"

test:
	@echo "=== test: layout + hub SQLite baseline ==="
	py -m pytest tests -q

fmt:
	@echo "=== fmt: stub until M0.2 (ruff format) ==="

lint:
	@echo "=== lint: stub until M0.2 (ruff check) ==="

compose-hub:
	@echo "=== compose-hub: deploy/compose/hub.yml arrives in M0.3 ==="

compose-vault:
	@echo "=== compose-vault: vault compose arrives in M0.4 ==="
