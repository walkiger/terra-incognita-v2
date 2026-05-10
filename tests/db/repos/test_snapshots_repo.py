"""M1.7 — SnapshotsRepository."""

from __future__ import annotations

import time

import pytest
from ti_hub.db.connection import HubSQLite
from ti_hub.db.repos import SnapshotsRepository, UsersRepository
from ti_hub.db.repos.exceptions import (
    IllegalSnapshotStateError,
    SnapshotTooLargeError,
)

_SHA = "a" * 64
_SHA2 = "b" * 64
_SHA3 = "c" * 64


async def _make_hub() -> HubSQLite:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    return hub


@pytest.mark.asyncio
async def test_initiate_and_complete_happy_path() -> None:
    hub = await _make_hub()
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user = await users.create("snap-a@example.com", "$argon2id$h")

        snap = await snapshots.initiate(user.id, "full", 1024, _SHA)
        assert snap.status == "uploading"
        assert snap.r2_key == f"pending:{_SHA}"
        assert snap.scope == "full"
        assert snap.size_bytes == 1024

        done = await snapshots.complete(snap.id, "r2/real/key")
        await conn.commit()

    assert done.status == "ready"
    assert done.r2_key == "r2/real/key"
    assert done.id == snap.id


@pytest.mark.asyncio
async def test_initiate_idempotent_on_sha256() -> None:
    hub = await _make_hub()
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user = await users.create("snap-b@example.com", "$argon2id$h")

        first = await snapshots.initiate(user.id, "full", 512, _SHA)
        second = await snapshots.initiate(user.id, "full", 512, _SHA)
        await conn.commit()

    assert first.id == second.id


@pytest.mark.asyncio
async def test_initiate_raises_on_oversized() -> None:
    hub = await _make_hub()
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user = await users.create("snap-c@example.com", "$argon2id$h")

        with pytest.raises(SnapshotTooLargeError):
            await snapshots.initiate(user.id, "full", 64 * 1024 * 1024 + 1, _SHA)


@pytest.mark.asyncio
async def test_complete_raises_on_illegal_state() -> None:
    hub = await _make_hub()
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user = await users.create("snap-d@example.com", "$argon2id$h")

        snap = await snapshots.initiate(user.id, "incremental", 256, _SHA)
        await snapshots.complete(snap.id, "r2/key/one")
        await conn.commit()

    async with hub.write_session() as conn:
        snapshots = SnapshotsRepository(conn)
        with pytest.raises(IllegalSnapshotStateError):
            await snapshots.complete(snap.id, "r2/key/two")


@pytest.mark.asyncio
async def test_expire_older_than() -> None:
    hub = await _make_hub()
    now = int(time.time())
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user = await users.create("snap-e@example.com", "$argon2id$h")

        snap = await snapshots.initiate(user.id, "full", 128, _SHA)
        expired_ids = await snapshots.expire_older_than(now + 60)
        await conn.commit()

    assert snap.id in expired_ids

    async with hub.write_session() as conn:
        snapshots = SnapshotsRepository(conn)
        listing = await snapshots.list_for_user(user.id)
        await conn.commit()

    assert listing[0].status == "expired"


@pytest.mark.asyncio
async def test_cross_tenant_same_sha_independent() -> None:
    """Two users can initiate snapshots with the same sha256 — no collision."""
    hub = await _make_hub()
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user_a = await users.create("snap-x-a@example.com", "$argon2id$h")
        user_b = await users.create("snap-x-b@example.com", "$argon2id$h")

        snap_a = await snapshots.initiate(user_a.id, "full", 512, _SHA)
        snap_b = await snapshots.initiate(user_b.id, "full", 512, _SHA)
        await conn.commit()

    assert snap_a.id != snap_b.id
    assert snap_a.user_id == user_a.id
    assert snap_b.user_id == user_b.id


@pytest.mark.asyncio
async def test_expire_ready_snapshot() -> None:
    hub = await _make_hub()
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user = await users.create("snap-g@example.com", "$argon2id$h")

        snap = await snapshots.initiate(user.id, "full", 256, _SHA3)
        done = await snapshots.complete(snap.id, "r2/key/ready")
        assert done.status == "ready"

        expired = await snapshots.expire(snap.id)
        await conn.commit()

    assert expired.status == "expired"
    assert expired.id == snap.id


@pytest.mark.asyncio
async def test_expire_already_expired_raises() -> None:
    hub = await _make_hub()
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user = await users.create("snap-h@example.com", "$argon2id$h")

        snap = await snapshots.initiate(user.id, "incremental", 128, _SHA3)
        await snapshots.expire(snap.id)
        await conn.commit()

    async with hub.write_session() as conn:
        snapshots = SnapshotsRepository(conn)
        with pytest.raises(IllegalSnapshotStateError):
            await snapshots.expire(snap.id)


@pytest.mark.asyncio
async def test_list_for_user_tenant_isolation() -> None:
    hub = await _make_hub()
    async with hub.write_session() as conn:
        users = UsersRepository(conn)
        snapshots = SnapshotsRepository(conn)
        user_a = await users.create("snap-f-a@example.com", "$argon2id$h")
        user_b = await users.create("snap-f-b@example.com", "$argon2id$h")

        await snapshots.initiate(user_a.id, "full", 100, _SHA)
        await snapshots.initiate(user_b.id, "full", 200, _SHA2)
        await conn.commit()

    async with hub.write_session() as conn:
        snapshots = SnapshotsRepository(conn)
        a_list = await snapshots.list_for_user(user_a.id)
        b_list = await snapshots.list_for_user(user_b.id)

    assert len(a_list) == 1
    assert a_list[0].user_id == user_a.id
    assert len(b_list) == 1
    assert b_list[0].user_id == user_b.id
