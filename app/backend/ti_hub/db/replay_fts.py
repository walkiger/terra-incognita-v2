"""Replay events FTS5 indexer (M1.2).

Automated maintenance uses triggers on ``replay_events`` plus ``replay_fts_rebuild_signals``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import aiosqlite

from ti_hub.db.connection import HubSQLite
from ti_hub.db.settings import REPLAY_FTS_REBUILD_DEBOUNCE_S


@dataclass(slots=True)
class ReplayFTSMetrics:
    rebuild_success_total: int = 0
    rebuild_failure_total: int = 0
    append_rebuild_skipped_debounce_total: int = 0
    last_rebuild_ok_unix: int = field(default=0)


class ReplayFTSIndexer:
    """FTS5 helpers + debounced full rebuild (terra-075 style signal table)."""

    def __init__(
        self,
        hub: HubSQLite,
        *,
        debounce_s: float = REPLAY_FTS_REBUILD_DEBOUNCE_S,
        metrics: ReplayFTSMetrics | None = None,
    ) -> None:
        self._hub = hub
        self._debounce_s = debounce_s
        self.metrics = metrics or ReplayFTSMetrics()

    @property
    def debounce_s(self) -> float:
        return self._debounce_s

    async def _delete_fts_rows_for_rowids(
        self, conn: aiosqlite.Connection, rowids: list[int]
    ) -> None:
        """Contentless FTS5 requires indexed column values to delete by row."""

        for rid in rowids:
            cur = await conn.execute(
                "SELECT payload_json, kind FROM replay_events WHERE id = ?",
                (rid,),
            )
            old = await cur.fetchone()
            if old is None:
                continue
            await conn.execute(
                "INSERT INTO replay_events_fts(replay_events_fts, rowid, payload_text, kind) "
                "VALUES ('delete', ?, ?, ?)",
                (rid, str(old[0]), str(old[1])),
            )

    async def _rebuild_full_core(self, conn: aiosqlite.Connection) -> None:
        await conn.execute("INSERT INTO replay_events_fts(replay_events_fts) VALUES('delete-all')")
        await conn.execute(
            "INSERT INTO replay_events_fts(rowid, payload_text, kind) "
            "SELECT id, payload_json, kind FROM replay_events"
        )
        await conn.execute(
            "UPDATE replay_fts_rebuild_signals SET append_count_since_rebuild = 0 WHERE id = 1"
        )

    async def rebuild_full(self) -> None:
        """Danger path: clears FTS rows and reloads from ``replay_events``."""

        async with self._hub.write_session() as conn:
            try:
                await self._rebuild_full_core(conn)
                await conn.commit()
            except Exception:
                await conn.rollback()
                self.metrics.rebuild_failure_total += 1
                raise
        self.metrics.rebuild_success_total += 1
        self.metrics.last_rebuild_ok_unix = int(time.time())

    async def index_event(self, *, row_id: int, payload_text: str, kind: str) -> None:
        """Upsert one FTS row out-of-band (repair / ingestion without triggers)."""

        async with self._hub.write_session() as conn:
            cur = await conn.execute(
                "SELECT payload_json, kind FROM replay_events WHERE id = ?",
                (row_id,),
            )
            old = await cur.fetchone()
            if old is None:
                msg = f"replay_events row {row_id} not found"
                raise ValueError(msg)
            await conn.execute(
                "INSERT INTO replay_events_fts(replay_events_fts, rowid, payload_text, kind) "
                "VALUES ('delete', ?, ?, ?)",
                (row_id, str(old[0]), str(old[1])),
            )
            await conn.execute(
                "INSERT INTO replay_events_fts(rowid, payload_text, kind) VALUES (?,?,?)",
                (row_id, payload_text, kind),
            )
            await conn.commit()

    async def reindex_user(self, user_id: int, *, since: int | None = None) -> None:
        """Rebuild FTS projections for ``user_id`` (optional ``since`` unix filter)."""

        async with self._hub.write_session() as conn:
            if since is None:
                cur = await conn.execute(
                    "SELECT id FROM replay_events WHERE user_id = ? ORDER BY id",
                    (user_id,),
                )
            else:
                cur = await conn.execute(
                    "SELECT id FROM replay_events WHERE user_id = ? AND ts >= ? ORDER BY id",
                    (user_id, since),
                )
            rowids = [int(r[0]) for r in await cur.fetchall()]
            await self._delete_fts_rows_for_rowids(conn, rowids)
            if since is None:
                await conn.execute(
                    "INSERT INTO replay_events_fts(rowid, payload_text, kind) "
                    "SELECT id, payload_json, kind FROM replay_events WHERE user_id = ?",
                    (user_id,),
                )
            else:
                await conn.execute(
                    "INSERT INTO replay_events_fts(rowid, payload_text, kind) "
                    "SELECT id, payload_json, kind FROM replay_events "
                    "WHERE user_id = ? AND ts >= ?",
                    (user_id, since),
                )
            await conn.commit()

    async def try_rebuild_if_idle(self) -> bool:
        """If append signals exist and quiet for ``debounce_s``, perform ``rebuild_full``."""

        async with self._hub.write_session() as conn:
            cur = await conn.execute(
                "SELECT append_count_since_rebuild, last_append_unix "
                "FROM replay_fts_rebuild_signals WHERE id = 1"
            )
            row = await cur.fetchone()
            if row is None:
                return False
            count, last_unix = int(row[0]), float(row[1])
            now = time.time()

            if count == 0:
                return False
            if now - last_unix < self._debounce_s:
                self.metrics.append_rebuild_skipped_debounce_total += 1
                return False

            try:
                await self._rebuild_full_core(conn)
                await conn.commit()
            except Exception:
                await conn.rollback()
                self.metrics.rebuild_failure_total += 1
                raise

        self.metrics.rebuild_success_total += 1
        self.metrics.last_rebuild_ok_unix = int(time.time())
        return True
