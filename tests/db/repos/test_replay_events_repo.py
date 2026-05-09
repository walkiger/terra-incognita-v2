"""M1.6 — ``ReplayEventsRepository.append`` + ``count_by_kind``."""

from __future__ import annotations

import pytest
from models import ReplayEventDraft
from ti_hub.db.connection import HubSQLite
from ti_hub.db.repos import ReplayEventsRepository, RepositoryError, UsersRepository


async def _create_user(hub: HubSQLite, email: str) -> int:
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        user = await users.create(email, "$argon2id$h")
        await conn.commit()
        return user.id


@pytest.mark.asyncio
async def test_append_round_trips_and_writes_to_fts() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid = await _create_user(hub, "replay-a@example.com")

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        draft = ReplayEventDraft(
            ts=10,
            kind="encounter",
            payload={"word": "needle", "scale": 1.0},
        )
        created = await repo.append(uid, draft)
        await conn.commit()

    assert created.id > 0
    assert created.user_id == uid
    assert created.ts == 10
    assert created.kind == "encounter"
    assert created.payload == {"word": "needle", "scale": 1.0}
    assert created.schema_ver == 1

    async with hub.write_session() as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM replay_events_fts WHERE replay_events_fts MATCH ?",
            ("needle",),
        )
        row = await cur.fetchone()
        assert row is not None
        assert int(row[0]) == 1
    await hub.close()


@pytest.mark.asyncio
async def test_count_by_kind_groups_per_user() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    uid_a = await _create_user(hub, "rk-a@example.com")
    uid_b = await _create_user(hub, "rk-b@example.com")

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        await repo.append(uid_a, ReplayEventDraft(ts=1, kind="encounter", payload={}))
        await repo.append(uid_a, ReplayEventDraft(ts=2, kind="encounter", payload={}))
        await repo.append(uid_a, ReplayEventDraft(ts=3, kind="snapshot", payload={}))
        await repo.append(uid_b, ReplayEventDraft(ts=4, kind="encounter", payload={}))
        await conn.commit()

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        hist_a = await repo.count_by_kind(uid_a)
        hist_b = await repo.count_by_kind(uid_b)
        hist_empty = await repo.count_by_kind(999)

    assert hist_a == {"encounter": 2, "snapshot": 1}
    assert hist_b == {"encounter": 1}
    assert hist_empty == {}
    await hub.close()


@pytest.mark.asyncio
async def test_append_rejects_invalid_user_id() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        with pytest.raises(ValueError):
            await repo.append(0, ReplayEventDraft(ts=0, kind="t", payload={}))
        with pytest.raises(ValueError):
            await repo.append(-1, ReplayEventDraft(ts=0, kind="t", payload={}))
    await hub.close()


@pytest.mark.asyncio
async def test_append_unknown_user_raises_repository_error() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()

    async with hub.write_session() as conn:
        repo = ReplayEventsRepository(conn)
        with pytest.raises(RepositoryError):
            await repo.append(404, ReplayEventDraft(ts=0, kind="t", payload={}))
    await hub.close()
