"""M1.4 — UsersRepository."""

from __future__ import annotations

from typing import Any, cast

import pytest
from ti_hub.db.connection import HubSQLite
from ti_hub.db.repos import EmailAlreadyRegistered, RepositoryError, UsersRepository


@pytest.mark.asyncio
async def test_create_and_fetch_by_email() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        created = await repo.create("alice@example.com", "$argon2id$dummyhash")
        await conn.commit()

    assert created.email == "alice@example.com"
    assert created.status == "active"
    assert not created.is_admin

    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        fetched = await repo.get_by_email("alice@example.com")
        assert fetched is not None
        assert fetched.id == created.id
        same_id = await repo.get_by_id(created.id)
        assert same_id == fetched
        assert await repo.count_active() == 1


@pytest.mark.asyncio
async def test_duplicate_email_raises() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        await repo.create("dup@example.com", "$argon2id$h1")
        await conn.commit()

    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        with pytest.raises(EmailAlreadyRegistered):
            await repo.create("dup@example.com", "$argon2id$h2")


@pytest.mark.asyncio
async def test_status_update() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        u = await repo.create("bob@example.com", "$argon2id$h")
        await conn.commit()

    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        await repo.update_status(u.id, "disabled")
        await conn.commit()

    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        bob = await repo.get_by_id(u.id)
        assert bob is not None
        assert bob.status == "disabled"
        assert await repo.count_active() == 0


@pytest.mark.asyncio
async def test_admin_flag() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        u = await repo.create("admin@example.com", "$argon2id$h")
        await repo.set_admin(u.id, True)
        await conn.commit()

    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        loaded = await repo.get_by_id(u.id)
        assert loaded is not None
        assert loaded.is_admin


@pytest.mark.asyncio
async def test_invalid_status_raises_repository_error() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        u = await repo.create("carol@example.com", "$argon2id$h")
        await conn.commit()

    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        bogus = cast(Any, "not_a_status")
        with pytest.raises(RepositoryError):
            await repo.update_status(u.id, bogus)


@pytest.mark.asyncio
async def test_get_by_id_unknown_returns_none() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        assert await repo.get_by_id(404) is None


@pytest.mark.asyncio
async def test_get_by_id_non_positive_raises() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        with pytest.raises(ValueError, match="must be positive"):
            await repo.get_by_id(0)


@pytest.mark.asyncio
async def test_get_by_email_unknown_returns_none() -> None:
    hub = HubSQLite(":memory:")
    await hub.connect()
    await hub.init_schema()
    async with hub.write_session() as conn:
        repo = UsersRepository(conn)
        assert await repo.get_by_email("nobody@example.com") is None
