"""Snapshots repository (M1.7)."""

from __future__ import annotations

import sqlite3
import time
from typing import Any, cast

from models.snapshot import Snapshot, SnapshotScope, SnapshotStatus

from .base import BaseRepository
from .exceptions import (
    IllegalSnapshotStateError,
    RepositoryError,
    SnapshotTooLargeError,
)

_MAX_SIZE_BYTES = 64 * 1024 * 1024  # 64 MB

_COLS = "id, user_id, ts, scope, size_bytes, content_sha256, r2_key, status"


def _row_to_snapshot(row: tuple[Any, ...]) -> Snapshot:
    _id, user_id, ts, scope, size_bytes, content_sha256, r2_key, status = row
    return Snapshot(
        id=int(_id),
        user_id=int(user_id),
        ts=int(ts),
        scope=cast(SnapshotScope, str(scope)),
        size_bytes=int(size_bytes),
        content_sha256=str(content_sha256),
        r2_key=str(r2_key),
        status=cast(SnapshotStatus, str(status)),
    )


class SnapshotsRepository(BaseRepository):
    async def initiate(
        self,
        user_id: int,
        scope: SnapshotScope,
        expected_size_bytes: int,
        content_sha256: str,
    ) -> Snapshot:
        """Begin a snapshot upload; idempotent on ``content_sha256``."""
        uid = self.require_positive_user_id(user_id)
        if expected_size_bytes > _MAX_SIZE_BYTES:
            raise SnapshotTooLargeError(expected_size_bytes, _MAX_SIZE_BYTES)

        # Idempotency: return existing row for same sha256 + user
        cur = await self.conn.execute(
            f"SELECT {_COLS} FROM snapshots WHERE content_sha256 = ? AND user_id = ?",
            (content_sha256, uid),
        )
        existing = await cur.fetchone()
        if existing is not None:
            return _row_to_snapshot(tuple(existing))

        provisional_r2_key = f"pending:{content_sha256}"
        ts = int(time.time())
        try:
            cur = await self.conn.execute(
                """
                INSERT INTO snapshots
                    (user_id, ts, scope, size_bytes, content_sha256, r2_key, status)
                VALUES (?, ?, ?, ?, ?, ?, 'uploading')
                """,
                (uid, ts, scope, expected_size_bytes, content_sha256, provisional_r2_key),
            )
            new_id = cur.lastrowid
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(str(exc)) from exc
        assert new_id is not None
        sel = await self.conn.execute(
            f"SELECT {_COLS} FROM snapshots WHERE id = ?",
            (int(new_id),),
        )
        row = await sel.fetchone()
        assert row is not None
        return _row_to_snapshot(tuple(row))

    async def complete(self, snapshot_id: int, r2_key: str) -> Snapshot:
        """Mark snapshot ``ready``; only valid from ``uploading`` state."""
        cur = await self.conn.execute(
            f"SELECT {_COLS} FROM snapshots WHERE id = ?",
            (snapshot_id,),
        )
        row = await cur.fetchone()
        if row is None:
            raise RepositoryError(f"snapshot {snapshot_id} not found")
        snap = _row_to_snapshot(tuple(row))
        if snap.status != "uploading":
            raise IllegalSnapshotStateError(snapshot_id, snap.status, "complete")
        try:
            await self.conn.execute(
                "UPDATE snapshots SET status = 'ready', r2_key = ? WHERE id = ?",
                (r2_key, snapshot_id),
            )
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(str(exc)) from exc
        sel = await self.conn.execute(
            f"SELECT {_COLS} FROM snapshots WHERE id = ?",
            (snapshot_id,),
        )
        updated = await sel.fetchone()
        assert updated is not None
        return _row_to_snapshot(tuple(updated))

    async def expire(self, snapshot_id: int) -> Snapshot:
        """Explicitly expire a snapshot; valid from ``uploading`` or ``ready``."""
        cur = await self.conn.execute(
            f"SELECT {_COLS} FROM snapshots WHERE id = ?",
            (snapshot_id,),
        )
        row = await cur.fetchone()
        if row is None:
            raise RepositoryError(f"snapshot {snapshot_id} not found")
        snap = _row_to_snapshot(tuple(row))
        if snap.status == "expired":
            raise IllegalSnapshotStateError(snapshot_id, snap.status, "expire")
        await self.conn.execute(
            "UPDATE snapshots SET status = 'expired' WHERE id = ?",
            (snapshot_id,),
        )
        sel = await self.conn.execute(
            f"SELECT {_COLS} FROM snapshots WHERE id = ?",
            (snapshot_id,),
        )
        updated = await sel.fetchone()
        assert updated is not None
        return _row_to_snapshot(tuple(updated))

    async def expire_older_than(self, threshold_ts: int) -> list[int]:
        """Expire all non-ready snapshots older than ``threshold_ts``.

        Marks ``uploading`` snapshots with ``ts < threshold_ts`` as ``expired``
        and returns the list of affected IDs.
        """
        cur = await self.conn.execute(
            """
            SELECT id FROM snapshots
            WHERE status = 'uploading' AND ts < ?
            """,
            (threshold_ts,),
        )
        rows = await cur.fetchall()
        ids = [int(r[0]) for r in rows]
        if ids:
            placeholders = ",".join("?" * len(ids))
            await self.conn.execute(
                f"UPDATE snapshots SET status = 'expired' WHERE id IN ({placeholders})",
                ids,
            )
        return ids

    async def list_for_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
    ) -> list[Snapshot]:
        uid = self.require_positive_user_id(user_id)
        if limit <= 0:
            msg = "limit must be positive"
            raise ValueError(msg)
        cur = await self.conn.execute(
            f"""
            SELECT {_COLS} FROM snapshots
            WHERE user_id = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (uid, limit),
        )
        rows = await cur.fetchall()
        return [_row_to_snapshot(tuple(r)) for r in rows]
