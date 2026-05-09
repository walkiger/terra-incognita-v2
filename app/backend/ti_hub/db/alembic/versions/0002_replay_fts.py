"""Replay FTS DDL sourced from ``schema/0002_replay_fts.sql``."""

import sqlite3
from pathlib import Path
from typing import cast

from alembic import op

revision = "0002_replay_fts"
down_revision = "0001_baseline"

_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schema"


def upgrade() -> None:
    ddl = (_SCHEMA_ROOT / "0002_replay_fts.sql").read_text(encoding="utf-8")
    conn = op.get_bind()
    raw = cast(sqlite3.Connection, conn.connection.dbapi_connection)
    raw.executescript(ddl)


def downgrade() -> None:
    """No-op intentional — restores via Litestream snapshot/R2 (never downgrade prod)."""
