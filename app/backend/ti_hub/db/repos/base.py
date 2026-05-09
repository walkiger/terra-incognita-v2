"""Shared helpers for SQLite repositories (M1.4+)."""

from __future__ import annotations

import aiosqlite


class BaseRepository:
    """Each repository holds a writer ``aiosqlite`` connection.

    Tenant isolation: every query that scopes data must receive ``user_id``
    explicitly from callers — repositories never infer the current principal.
    """

    __slots__ = ("_conn",)

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    @property
    def conn(self) -> aiosqlite.Connection:
        return self._conn

    def require_positive_user_id(self, user_id: int, *, field: str = "user_id") -> int:
        """Guard against accidental zero/negative tenant keys."""

        if user_id <= 0:
            msg = f"{field} must be positive, got {user_id}"
            raise ValueError(msg)
        return user_id
