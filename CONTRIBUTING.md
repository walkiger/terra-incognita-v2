# Contributing

**Produktcode:** [`app/README.md`](app/README.md) · **Deploy/Infra:** [`deploy/README.md`](deploy/README.md) · **Branch-/PR-Kanon:** [`docs/operations/branch-and-pr-rules.md`](docs/operations/branch-and-pr-rules.md)

## Pflichtlektüre

1. [`app/docs/greenfield/README.md`](app/docs/greenfield/README.md) (Lesepfad)
2. Aktuelle MVP-Phase in [`app/docs/greenfield/implementation/mvp/00-index.md`](app/docs/greenfield/implementation/mvp/00-index.md)
3. [`CLAUDE.md`](CLAUDE.md), [`Anweisungen.md`](Anweisungen.md)

## Schnellstart

| Aufgabe                            | Kommando                                                                                                                                                                                                                                                                                                                                    |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dependencies                       | **`uv sync --extra dev`** oder **`make bootstrap`** (inkl. Pre-commit-Hooks)                                                                                                                                                                                                                                                                |
| Tests (ohne Docker-Compose-Marker) | **`make test`** oder **`uv run pytest tests -q -m "not compose_hub and not compose_vault and not compose_observability and not compose_litestream and not compose_r2_pull and not alembic_isolation"`** · Alembic: **`uv run pytest tests/db/test_alembic_migrations.py -q`** (läuft in CI zusätzlich unter **`migration-roundtrip-test`**) |
| Format / Lint                      | **`make fmt`** / **`make lint`** (Ziele **`app/backend/api`**, **`app/backend/ti_hub`**, **`app/backend/models`**, **`tests`**)                                                                                                                                                                                                             |
| Hub/Vault Compose (Quick-Tunnel)   | **`make compose-hub`** / **`make compose-vault`**                                                                                                                                                                                                                                                                                           |
| Secrets decrypt                    | **`make secrets-decrypt`** (benötigt **`sops`** und **`SOPS_AGE_KEY_FILE`**, siehe [`secrets/README.md`](secrets/README.md))                                                                                                                                                                                                                |

- **Litestream / Hub backup:** Compose-Profil **`litestream`** + Operatorhandbuch [`docs/operations/litestream.md`](docs/operations/litestream.md).
- **Restore drill:** [`docs/operations/restore-drill.md`](docs/operations/restore-drill.md) · [`scripts/operations/restore_hub.sh`](scripts/operations/restore_hub.sh).

Windows: GNU **`make`** (Git Bash/WSL). **`py`** für lokale Tool-Aufrufe siehe **`CLAUDE.md`**.

**Legacy-Hinweis:** Root-**`requirements-ci.txt`**/**`pytest.ini`** wurden durch **`pyproject.toml`** + **`uv.lock`** ersetzt (M0.2).
