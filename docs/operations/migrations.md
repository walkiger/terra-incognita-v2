# Hub SQLite migrations (Alembic)

Operational notes for **`app/backend/ti_hub/db`**: **`TI_HUB_ALEMBIC_URL`** conventionally uses **`sqlite+aiosqlite:///…`** (same as the Hub app). The Alembic CLI normalizes this to **`sqlite:///…`** internally so DDL can run via **`sqlite3.Connection.executescript`**.

## URL and config

- Prefer environment variable **`TI_HUB_ALEMBIC_URL`**, e.g. `sqlite+aiosqlite:///var/lib/ti/hub.sqlite` (absolute path on the host).
- Config file: `app/backend/ti_hub/db/alembic.ini`. If the env var is unset, `sqlalchemy.url` in that file is used; the placeholder path is rejected at runtime until you set a real URL or edit the INI.

Offline mode (`alembic revision --sql`, etc.) is disabled in `alembic/env.py` for this stack.

## Apply migrations

From the repository root:

```bash
uv run alembic -c app/backend/ti_hub/db/alembic.ini upgrade head
```

Or use `make migrate` (same command; still requires `TI_HUB_ALEMBIC_URL` when using the placeholder INI URL).

## New revisions

- **Source of truth** for DDL remains the ordered files under `app/backend/ti_hub/db/schema/` (`0001_baseline.sql`, `0002_replay_fts.sql`, …).
- New Alembic steps should load the matching file and run it on the DBAPI connection with `executescript` (see existing revisions under `alembic/versions/`).
- **`downgrade()`** is intentionally a no-op: recovery is **not** via Alembic downgrades.
- Production **never** runs `alembic downgrade`. Roll back by restoring a SQLite file from Litestream / R2 (MVP disaster-recovery runbooks under `app/docs/greenfield/runbooks/`).

## Emergency rollback

1. Stop writers touching the corrupted database (prefer taking the Hub offline).
2. Restore from the latest Litestream-backed snapshot / R2 object set per operations runbooks.
3. Point the Hub at the restored file (or rotate to a new path), then restart.
4. If the restored DB has no Alembic row or trails the repo revisions, run **`alembic upgrade head`** forward only—not down.

## Tests

Round-trip and idempotence checks live in `tests/db/test_alembic_migrations.py` (marker `alembic_isolation`). They are excluded from the default `make test` / main CI pytest run to avoid duplicate work; CI runs them in the **`migration-roundtrip-test`** job.

```bash
uv run pytest tests/db/test_alembic_migrations.py -q
```
