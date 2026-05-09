"""M1.5 — EncountersRepository."""

from __future__ import annotations

import time
from typing import Any, cast

import pytest
from models import EncounterDraft
from pydantic import ValidationError
from ti_hub.db.connection import HubSQLite
from ti_hub.db.repos import EncountersRepository, RepositoryError, UsersRepository


@pytest.mark.asyncio
async def test_append_and_list() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()

    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        encounters = EncountersRepository(conn)
        user = await users.create("encounters-a@example.com", "$argon2id$h")
        draft = EncounterDraft(
            word="hello",
            scale=1.25,
            source="user_input",
            context={"note": "ctx"},
        )
        created = await encounters.append(user.id, draft)
        await conn.commit()

    assert created.word == "hello"
    assert created.scale == 1.25
    assert created.source == "user_input"
    assert created.context == {"note": "ctx"}

    async with hub.write_session() as conn:
        encounters = EncountersRepository(conn)
        rows = await encounters.list_for_user(user.id)
        assert len(rows) == 1
        assert rows[0].id == created.id


@pytest.mark.asyncio
async def test_source_whitelist_pydantic() -> None:
    with pytest.raises(ValidationError):
        EncounterDraft(scale=1.0, source=cast(Any, "invalid_source"), context={})


@pytest.mark.asyncio
async def test_index_used() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()

    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        encounters = EncountersRepository(conn)
        user = await users.create("encounters-idx@example.com", "$argon2id$h")
        await encounters.append(user.id, EncounterDraft(scale=2.0, source="ghost", context={}))
        await conn.commit()

    async with hub.write_session() as conn:
        cur = await conn.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT id FROM encounters
            WHERE user_id = ?
            ORDER BY ts DESC
            LIMIT 10
            """,
            (user.id,),
        )
        explain_rows = await cur.fetchall()

    plan_blob = " ".join(str(cell).lower() for row in explain_rows for cell in row)
    assert "idx_encounters_user_ts" in plan_blob


@pytest.mark.asyncio
async def test_cross_user_fk_append() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()

    async with hub.write_session() as conn:
        encounters = EncountersRepository(conn)
        with pytest.raises(RepositoryError):
            await encounters.append(404, EncounterDraft(scale=1.0, source="replay", context={}))


@pytest.mark.asyncio
async def test_count_for_user_within_window() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()

    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        encounters = EncountersRepository(conn)
        user = await users.create("encounters-win@example.com", "$argon2id$h")
        row = await encounters.append(user.id, EncounterDraft(scale=1.0, source="walk", context={}))
        assert await encounters.count_for_user_within(user.id, window_seconds=86_400) >= 1

        old_ts = int(time.time()) - 48 * 3600
        await conn.execute(
            "UPDATE encounters SET ts = ? WHERE id = ?",
            (old_ts, row.id),
        )
        await conn.commit()

    async with hub.write_session() as conn:
        encounters = EncountersRepository(conn)
        assert await encounters.count_for_user_within(user.id, window_seconds=3600) == 0
