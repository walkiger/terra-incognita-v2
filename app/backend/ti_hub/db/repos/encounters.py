"""Encounters repository (M1.5)."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, cast

from models.encounter import Encounter, EncounterDraft, EncounterSource

from .base import BaseRepository
from .exceptions import RepositoryError


def _row_to_encounter(row: tuple[Any, ...]) -> Encounter:
    _id, user_id, ts, word, scale, source, context_json = row
    ctx_raw = str(context_json)
    try:
        decoded = json.loads(ctx_raw)
    except json.JSONDecodeError as exc:
        msg = f"invalid context_json for encounter {_id}"
        raise RepositoryError(msg) from exc
    if not isinstance(decoded, dict):
        msg = f"context_json must decode to object for encounter {_id}"
        raise RepositoryError(msg)
    return Encounter(
        id=int(_id),
        user_id=int(user_id),
        ts=int(ts),
        word=None if word is None else str(word),
        scale=float(scale),
        source=cast(EncounterSource, str(source)),
        context=decoded,
    )


class EncountersRepository(BaseRepository):
    async def append(self, user_id: int, encounter: EncounterDraft) -> Encounter:
        uid = self.require_positive_user_id(user_id)
        payload = json.dumps(encounter.context)
        ts = int(time.time())
        try:
            cur = await self.conn.execute(
                """
                INSERT INTO encounters (user_id, ts, word, scale, source, context_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (uid, ts, encounter.word, encounter.scale, encounter.source, payload),
            )
            new_id = cur.lastrowid
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(str(exc)) from exc
        assert new_id is not None
        sel = await self.conn.execute(
            """
            SELECT id, user_id, ts, word, scale, source, context_json
            FROM encounters WHERE id = ?
            """,
            (int(new_id),),
        )
        row = await sel.fetchone()
        assert row is not None
        return _row_to_encounter(tuple(row))

    async def list_for_user(
        self,
        user_id: int,
        *,
        since: int | None = None,
        limit: int = 100,
    ) -> list[Encounter]:
        uid = self.require_positive_user_id(user_id)
        if limit <= 0:
            msg = "limit must be positive"
            raise ValueError(msg)

        if since is None:
            cur = await self.conn.execute(
                """
                SELECT id, user_id, ts, word, scale, source, context_json
                FROM encounters
                WHERE user_id = ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (uid, limit),
            )
        else:
            cur = await self.conn.execute(
                """
                SELECT id, user_id, ts, word, scale, source, context_json
                FROM encounters
                WHERE user_id = ? AND ts > ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (uid, since, limit),
            )
        rows = await cur.fetchall()
        return [_row_to_encounter(tuple(r)) for r in rows]

    async def count_for_user_within(self, user_id: int, window_seconds: int) -> int:
        uid = self.require_positive_user_id(user_id)
        if window_seconds <= 0:
            msg = "window_seconds must be positive"
            raise ValueError(msg)
        cutoff = int(time.time()) - window_seconds
        cur = await self.conn.execute(
            """
            SELECT COUNT(*) FROM encounters
            WHERE user_id = ? AND ts >= ?
            """,
            (uid, cutoff),
        )
        row = await cur.fetchone()
        assert row is not None
        return int(row[0])
