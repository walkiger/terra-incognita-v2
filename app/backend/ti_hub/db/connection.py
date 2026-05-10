"""Async SQLite connection manager for the Hub (M1.1+) including ordered schema files (M1.2 FTS).

See ``app/docs/greenfield/implementation/mvp/M1-data-foundation.md`` § M1.1 / § M1.2.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Final

import aiosqlite

_SCHEMA_DIR: Final = Path(__file__).resolve().parent / "schema"
_SCHEMA_FILES: Final[tuple[Path, ...]] = (
    _SCHEMA_DIR / "0001_baseline.sql",
    _SCHEMA_DIR / "0002_replay_fts.sql",
    _SCHEMA_DIR / "0003_encounters_source_check.sql",
    _SCHEMA_DIR / "0004_snapshot_unique_per_user.sql",
)

_PRAGMA_BOOTSQL: Final = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;
PRAGMA cache_size=-8192;
PRAGMA temp_store=MEMORY;
"""

SCHEMA_VERSION: Final[int] = 4
APP_VERSION: Final[str] = "0.2.0-dev"


def _safe_pragma(name: str) -> str:
    if not name or not all(ch.isalnum() or ch == "_" for ch in name):
        msg = f"invalid pragma name: {name!r}"
        raise ValueError(msg)
    return name


async def _apply_pragmas(conn: aiosqlite.Connection) -> None:
    await conn.executescript(_PRAGMA_BOOTSQL)


async def open_readonly_connection(database_path: Path) -> aiosqlite.Connection:
    """Open a second SQLite connection in read-only mode (parallel reads).

    Not used for ``:memory:`` databases — use the writer connection only there.
    """

    uri = database_path.expanduser().resolve().as_uri()
    ro_uri = f"{uri}?mode=ro"
    conn = await aiosqlite.connect(ro_uri, uri=True)
    await conn.execute("PRAGMA query_only=ON;")
    return conn


class HubSQLite:
    """Single writer connection + asyncio lock; optional parallel readers via RO URIs."""

    def __init__(self, database: str) -> None:
        self._database = database
        self._write: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._write is not None:
            return
        self._write = await aiosqlite.connect(self._database)
        await _apply_pragmas(self._write)

    async def close(self) -> None:
        if self._write is not None:
            await self._write.close()
            self._write = None

    @asynccontextmanager
    async def write_session(self) -> AsyncIterator[aiosqlite.Connection]:
        """Serialize writer access; caller must ``commit`` when mutating data."""

        async with self._write_lock:
            if self._write is None:
                msg = "connect() before write_session()"
                raise RuntimeError(msg)
            yield self._write

    async def init_schema(self, sql_path: Path | None = None) -> None:
        """Apply ordered DDL files and seed ``meta``."""

        paths: tuple[Path, ...] = (sql_path,) if sql_path is not None else _SCHEMA_FILES
        ddl = "\n".join(p.read_text(encoding="utf-8") for p in paths)
        async with self._write_lock:
            if self._write is None:
                msg = "connect() before init_schema()"
                raise RuntimeError(msg)
            await self._write.executescript(ddl)
            await self._write.commit()
            await self._seed_meta_locked()

    async def _seed_meta_locked(self) -> None:
        assert self._write is not None
        cur = await self._write.execute("SELECT COUNT(*) FROM meta")
        row = await cur.fetchone()
        count = int(row[0]) if row else 0
        if count == 0:
            await self._write.execute(
                "INSERT INTO meta (schema_version, app_version, installed_at) VALUES (?, ?, ?)",
                (SCHEMA_VERSION, APP_VERSION, int(time.time())),
            )
            await self._write.commit()

    async def pragma_str(self, name: str) -> str:
        """Return main-connection pragma value (writer; serialized)."""

        async with self._write_lock:
            if self._write is None:
                msg = "connect() before pragma_str()"
                raise RuntimeError(msg)
            safe = _safe_pragma(name)
            cur = await self._write.execute(f"PRAGMA {safe}")
            row = await cur.fetchone()
            if row is None or row[0] is None:
                return ""
            return str(row[0])

    async def meta_row(self) -> tuple[int, str, int]:
        async with self._write_lock:
            if self._write is None:
                msg = "connect() before meta_row()"
                raise RuntimeError(msg)
            cur = await self._write.execute(
                "SELECT schema_version, app_version, installed_at FROM meta LIMIT 1"
            )
            row = await cur.fetchone()
            if row is None:
                msg = "meta row missing"
                raise RuntimeError(msg)
            return int(row[0]), str(row[1]), int(row[2])

    async def table_names(self) -> frozenset[str]:
        async with self._write_lock:
            if self._write is None:
                msg = "connect() before table_names()"
                raise RuntimeError(msg)
            cur = await self._write.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            rows = await cur.fetchall()
            return frozenset(str(r[0]) for r in rows if r[0])
