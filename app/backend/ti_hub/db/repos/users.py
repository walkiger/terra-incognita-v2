"""Users repository (M1.4)."""

from __future__ import annotations

import sqlite3
import time
from typing import Any, cast

from models.user import User, UserCredentials, UserStatus
from pydantic import EmailStr, TypeAdapter

from .base import BaseRepository
from .exceptions import raise_repository_integrity

_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _row_to_user(row: tuple[Any, ...]) -> User:
    _id, email, created_at, status, is_admin_int = row
    return User(
        id=int(_id),
        email=str(email),
        created_at=int(created_at),
        status=cast(UserStatus, str(status)),
        is_admin=bool(is_admin_int),
    )


class UsersRepository(BaseRepository):
    async def get_by_id(self, user_id: int) -> User | None:
        uid = self.require_positive_user_id(user_id)
        cur = await self.conn.execute(
            """
            SELECT id, email, created_at, status, is_admin
            FROM users
            WHERE id = ?
            """,
            (uid,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return _row_to_user(tuple(row))

    async def get_by_email(self, email: str) -> User | None:
        normalized = str(_EMAIL_ADAPTER.validate_python(email))
        cur = await self.conn.execute(
            """
            SELECT id, email, created_at, status, is_admin
            FROM users
            WHERE email = ?
            """,
            (normalized,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return _row_to_user(tuple(row))

    async def create(self, email: str, pwhash: str) -> User:
        creds = UserCredentials(email=email, pwhash_argon2=pwhash)
        ts = int(time.time())
        try:
            cur = await self.conn.execute(
                """
                INSERT INTO users (email, pwhash_argon2, created_at, status, is_admin)
                VALUES (?, ?, ?, 'active', 0)
                """,
                (str(creds.email), creds.pwhash_argon2, ts),
            )
            new_id = cur.lastrowid
        except sqlite3.IntegrityError as exc:
            raise_repository_integrity(exc, context_email=str(creds.email))
        assert new_id is not None
        loaded = await self.get_by_id(int(new_id))
        assert loaded is not None
        return loaded

    async def update_status(self, user_id: int, status: UserStatus) -> None:
        uid = self.require_positive_user_id(user_id)
        try:
            await self.conn.execute(
                "UPDATE users SET status = ? WHERE id = ?",
                (status, uid),
            )
        except sqlite3.IntegrityError as exc:
            raise_repository_integrity(exc)

    async def set_admin(self, user_id: int, is_admin: bool) -> None:
        uid = self.require_positive_user_id(user_id)
        await self.conn.execute(
            "UPDATE users SET is_admin = ? WHERE id = ?",
            (1 if is_admin else 0, uid),
        )

    async def count_active(self) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE status = 'active'",
        )
        row = await cur.fetchone()
        assert row is not None
        return int(row[0])
