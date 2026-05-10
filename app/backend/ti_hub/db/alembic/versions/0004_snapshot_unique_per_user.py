"""Per-user UNIQUE constraints on snapshots.content_sha256 and r2_key."""

import sqlite3
from pathlib import Path
from typing import cast

from alembic import op

revision = "0004_snapshot_unique_per_user"
down_revision = "0003_encounters_source"

_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schema"


def upgrade() -> None:
    ddl = (_SCHEMA_ROOT / "0004_snapshot_unique_per_user.sql").read_text(encoding="utf-8")
    conn = op.get_bind()
    raw = cast(sqlite3.Connection, conn.connection.dbapi_connection)
    raw.executescript(ddl)


def downgrade() -> None:
    """No-op intentional — restores via Litestream snapshot/R2 (never downgrade prod)."""
