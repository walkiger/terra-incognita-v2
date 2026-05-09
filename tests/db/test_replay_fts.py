"""M1.2 — FTS5 indexer for replay events."""

from __future__ import annotations

import time

import pytest
from ti_hub.db.connection import HubSQLite
from ti_hub.db.replay_fts import ReplayFTSIndexer, ReplayFTSMetrics


async def _insert_user(hub: HubSQLite, *, email: str = "u@example.test") -> int:
    async with hub.write_session() as conn:
        await conn.execute(
            "INSERT INTO users (email, pwhash_argon2, created_at, status) VALUES (?,?,?,?)",
            (email, "stub", 1, "active"),
        )
        cur = await conn.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        assert row is not None
        await conn.commit()
        return int(row[0])


async def _append_replay_event(
    hub: HubSQLite,
    *,
    user_id: int,
    ts: int,
    payload_json: str,
    kind: str = "encounter",
    schema_ver: int = 1,
) -> int:
    async with hub.write_session() as conn:
        await conn.execute(
            "INSERT INTO replay_events(user_id, ts, kind, payload_json, schema_ver)"
            " VALUES (?,?,?,?,?)",
            (user_id, ts, kind, payload_json, schema_ver),
        )
        cur = await conn.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        assert row is not None
        await conn.commit()
        return int(row[0])


async def _match_count(hub: HubSQLite, term: str) -> int:
    async with hub.write_session() as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM replay_events_fts WHERE replay_events_fts MATCH ?",
            (term,),
        )
        row = await cur.fetchone()
        assert row is not None
        return int(row[0])


@pytest.mark.asyncio
async def test_index_and_search_basic() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    metrics = ReplayFTSMetrics()
    indexer = ReplayFTSIndexer(hub, metrics=metrics)

    uid = await _insert_user(hub)
    await _append_replay_event(hub, user_id=uid, ts=10, payload_json='{"needle": true}', kind="k1")

    hits = await _match_count(hub, "needle")
    assert hits == 1

    await indexer.reindex_user(uid)
    hits_after = await _match_count(hub, "needle")
    assert hits_after == 1
    await hub.close()


@pytest.mark.asyncio
async def test_debounce_window_respected() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()

    uid = await _insert_user(hub)
    await _append_replay_event(hub, user_id=uid, ts=100, payload_json='"alpha"', kind="t")

    metrics = ReplayFTSMetrics()
    indexer = ReplayFTSIndexer(hub, debounce_s=3600.0, metrics=metrics)

    rebuilt = await indexer.try_rebuild_if_idle()
    assert rebuilt is False
    assert metrics.append_rebuild_skipped_debounce_total == 1

    past = int(time.time()) - 10_000
    async with hub.write_session() as conn:
        await conn.execute(
            "UPDATE replay_fts_rebuild_signals SET last_append_unix = ? WHERE id = 1",
            (past,),
        )
        await conn.commit()

    rebuilt2 = await indexer.try_rebuild_if_idle()
    assert rebuilt2 is True
    assert metrics.rebuild_success_total == 1
    await hub.close()


@pytest.mark.asyncio
async def test_index_event_explicit() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    indexer = ReplayFTSIndexer(hub)

    uid = await _insert_user(hub)
    rid = await _append_replay_event(hub, user_id=uid, ts=77, payload_json='"oldneedle"', kind="t")

    assert await _match_count(hub, "oldneedle") == 1

    await indexer.index_event(row_id=rid, payload_text='"newneedle"', kind="t")
    assert await _match_count(hub, "oldneedle") == 0
    assert await _match_count(hub, "newneedle") == 1
    await hub.close()


@pytest.mark.asyncio
async def test_rebuild_recovers_from_corruption() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()

    indexer = ReplayFTSIndexer(hub)

    uid = await _insert_user(hub)
    await _append_replay_event(hub, user_id=uid, ts=55, payload_json='"gamma-ray"', kind="x")

    assert await _match_count(hub, "gamma") == 1

    async with hub.write_session() as conn:
        await conn.execute("INSERT INTO replay_events_fts(replay_events_fts) VALUES('delete-all')")
        await conn.commit()

    assert await _match_count(hub, "gamma") == 0

    await indexer.rebuild_full()
    assert await _match_count(hub, "gamma") == 1
    await hub.close()
