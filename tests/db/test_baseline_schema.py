"""M1.1 — Hub SQLite baseline schema (tables + pragmas + meta)."""

import asyncio
from pathlib import Path

import pytest

from ti_hub.db.connection import (
    APP_VERSION,
    SCHEMA_VERSION,
    HubSQLite,
    open_readonly_connection,
)

_EXPECTED_TABLES = frozenset(
    {
        "users",
        "sessions",
        "engine_connections",
        "encounters",
        "replay_events",
        "snapshots",
        "meta",
    }
)


@pytest.mark.asyncio
async def test_schema_creates_all_tables() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    names = await hub.table_names()
    assert _EXPECTED_TABLES <= names
    assert "replay_events_fts" not in names
    await hub.close()


@pytest.mark.asyncio
async def test_pragmas_applied(tmp_path: Path) -> None:
    db_path = tmp_path / "hub.sqlite"
    hub = HubSQLite(str(db_path))
    await hub.connect()
    await hub.init_schema()
    assert (await hub.pragma_str("journal_mode")).lower() == "wal"
    assert (await hub.pragma_str("foreign_keys")) == "1"
    await hub.close()


@pytest.mark.asyncio
async def test_meta_schema_version_set(tmp_path: Path) -> None:
    hub = HubSQLite(str(tmp_path / "hub.sqlite"))
    await hub.connect()
    await hub.init_schema()
    sv, av, _installed = await hub.meta_row()
    assert sv == SCHEMA_VERSION
    assert av == APP_VERSION
    await hub.close()


@pytest.mark.asyncio
async def test_parallel_readonly_connections(tmp_path: Path) -> None:
    db_path = tmp_path / "hub.sqlite"
    hub = HubSQLite(str(db_path))
    await hub.connect()
    await hub.init_schema()

    async def read_sv() -> int:
        conn = await open_readonly_connection(db_path)
        try:
            cur = await conn.execute("SELECT schema_version FROM meta LIMIT 1")
            row = await cur.fetchone()
            assert row is not None
            return int(row[0])
        finally:
            await conn.close()

    results = await asyncio.gather(read_sv(), read_sv())
    assert results == [SCHEMA_VERSION, SCHEMA_VERSION]
    await hub.close()
