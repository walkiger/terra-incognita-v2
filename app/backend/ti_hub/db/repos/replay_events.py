"""Replay events repository (M1.6)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from models.replay_event import ReplayEvent, ReplayEventDraft

from .base import BaseRepository
from .exceptions import RepositoryError


def _row_to_replay_event(row: tuple[Any, ...]) -> ReplayEvent:
    _id, user_id, ts, kind, payload_json, schema_ver = row
    raw = str(payload_json)
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"invalid payload_json for replay_event {_id}"
        raise RepositoryError(msg) from exc
    if not isinstance(decoded, dict):
        msg = f"payload_json must decode to object for replay_event {_id}"
        raise RepositoryError(msg)
    return ReplayEvent(
        id=int(_id),
        user_id=int(user_id),
        ts=int(ts),
        kind=str(kind),
        payload=decoded,
        schema_ver=int(schema_ver),
    )


class ReplayEventsRepository(BaseRepository):
    async def append(self, user_id: int, draft: ReplayEventDraft) -> ReplayEvent:
        """Insert one row and return the materialised :class:`ReplayEvent`.

        FTS5 projection is maintained by triggers in ``schema/0002_replay_fts.sql``;
        callers don't need to touch the FTS table.
        """

        uid = self.require_positive_user_id(user_id)
        payload_text = json.dumps(draft.payload)
        try:
            cur = await self.conn.execute(
                """
                INSERT INTO replay_events (user_id, ts, kind, payload_json, schema_ver)
                VALUES (?, ?, ?, ?, ?)
                """,
                (uid, draft.ts, draft.kind, payload_text, draft.schema_ver),
            )
            new_id = cur.lastrowid
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(str(exc)) from exc
        assert new_id is not None
        sel = await self.conn.execute(
            """
            SELECT id, user_id, ts, kind, payload_json, schema_ver
            FROM replay_events
            WHERE id = ?
            """,
            (int(new_id),),
        )
        row = await sel.fetchone()
        assert row is not None
        return _row_to_replay_event(tuple(row))

    async def count_by_kind(self, user_id: int) -> dict[str, int]:
        """Per-tenant histogram. Used by ``/v1/diagnostic`` (M5.9)."""

        uid = self.require_positive_user_id(user_id)
        cur = await self.conn.execute(
            """
            SELECT kind, COUNT(*)
            FROM replay_events
            WHERE user_id = ?
            GROUP BY kind
            """,
            (uid,),
        )
        rows = await cur.fetchall()
        return {str(r[0]): int(r[1]) for r in rows}
