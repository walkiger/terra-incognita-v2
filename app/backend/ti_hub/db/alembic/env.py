"""Alembic env for Hub SQLite.

Migrations execute canonical ``schema/*.sql`` scripts via ``sqlite3.Connection.executescript``.
Alembic therefore uses a **synchronous** ``sqlite:///`` engine; ``TI_HUB_ALEMBIC_URL`` may
still use ``sqlite+aiosqlite:`` — it is normalized here for this CLI-only process.

Reads URL from ``TI_HUB_ALEMBIC_URL`` then ``sqlalchemy.url`` in ``alembic.ini``.
"""

from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection, make_url

config = context.config

if config.config_file_name:
    ini_path = Path(config.config_file_name).resolve()
    fileConfig(str(ini_path), disable_existing_loggers=False)


def _configured_url_raw() -> str:
    env_url = os.environ.get("TI_HUB_ALEMBIC_URL")
    if env_url:
        return env_url
    ini_url = config.get_main_option("sqlalchemy.url") or ""
    if ini_url.endswith("placeholder.sqlite"):
        msg = (
            "Set TI_HUB_ALEMBIC_URL (e.g. sqlite+aiosqlite:///PATH/hub.sqlite) "
            "or fix sqlalchemy.url in alembic.ini"
        )
        raise RuntimeError(msg)
    return ini_url


def _sync_sqlite_url() -> str:
    raw = _configured_url_raw()
    parsed = make_url(raw)
    if parsed.drivername not in ("sqlite", "sqlite+aiosqlite"):
        msg = f"Hub migrations expect a sqlite URL, got {parsed.drivername!r}"
        raise RuntimeError(msg)
    sync = parsed.set(drivername="sqlite")
    return sync.render_as_string(hide_password=False)


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        compare_type=False,
        target_metadata=None,
        render_as_batch=False,
        transactional_ddl=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_sync_sqlite_url(), poolclass=pool.NullPool)
    try:
        with connectable.connect() as connection:
            do_run_migrations(connection)
    finally:
        connectable.dispose()


def run_migrations_offline() -> None:
    """Offline mode not used — fail fast."""

    raise RuntimeError("Alembic offline migrations are disabled for Hub SQLite")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
