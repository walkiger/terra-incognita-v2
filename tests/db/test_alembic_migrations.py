"""M1.3 — Alembic revisions mirror canonical ``schema/*.sql`` DDL."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from sqlalchemy.engine.url import URL

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _REPO_ROOT / "app" / "backend" / "ti_hub" / "db" / "alembic.ini"
_SCHEMA_DIR = _REPO_ROOT / "app" / "backend" / "ti_hub" / "db" / "schema"


def _sqlite_aiosqlite_url(path: Path) -> str:
    return URL.create(
        drivername="sqlite+aiosqlite",
        database=str(path.resolve()),
    ).render_as_string(hide_password=False)


def _sqlite_master_rows(con: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    cur = con.execute(
        """
        SELECT type, name, tbl_name, ifnull(sql, '')
        FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%'
          AND name != 'alembic_version'
        ORDER BY type, name, tbl_name, sql
        """
    )
    return [(str(r[0]), str(r[1]), str(r[2]), str(r[3])) for r in cur.fetchall()]


def _run_alembic(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(_ALEMBIC_INI), *args],
        cwd=_REPO_ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )


SchemaRow = tuple[str, str, str, str]


def assert_schema_equal(a: Sequence[SchemaRow], b: Sequence[SchemaRow]) -> None:
    if list(a) == list(b):
        return
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    msg_lines = ["sqlite_master divergence (excluding alembic_version, sqlite_*)."]
    if only_a:
        msg_lines.append(f"Only in first: {only_a}")
    if only_b:
        msg_lines.append(f"Only in second: {only_b}")
    pytest.fail("\n".join(msg_lines))


@pytest.mark.alembic_isolation
def test_upgrade_head_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "hub.sqlite"
    url = _sqlite_aiosqlite_url(db)
    base = os.environ.copy()
    base["TI_HUB_ALEMBIC_URL"] = url

    r1 = _run_alembic(base, "upgrade", "head")
    assert r1.returncode == 0, (r1.stdout, r1.stderr)
    r2 = _run_alembic(base, "upgrade", "head")
    assert r2.returncode == 0, (r2.stdout, r2.stderr)


@pytest.mark.alembic_isolation
def test_migration_roundtrip_no_diff(tmp_path: Path) -> None:
    db_a = tmp_path / "via_alembic.sqlite"
    db_b = tmp_path / "via_scripts.sqlite"

    env = os.environ.copy()
    env["TI_HUB_ALEMBIC_URL"] = _sqlite_aiosqlite_url(db_a)

    proc = _run_alembic(env, "upgrade", "head")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)

    con_b = sqlite3.connect(db_b)
    try:
        con_b.execute("PRAGMA foreign_keys=ON;")
        ddl1 = (_SCHEMA_DIR / "0001_baseline.sql").read_text(encoding="utf-8")
        ddl2 = (_SCHEMA_DIR / "0002_replay_fts.sql").read_text(encoding="utf-8")
        ddl3 = (_SCHEMA_DIR / "0003_encounters_source_check.sql").read_text(encoding="utf-8")
        ddl4 = (_SCHEMA_DIR / "0004_snapshot_unique_per_user.sql").read_text(encoding="utf-8")
        con_b.executescript(ddl1)
        con_b.executescript(ddl2)
        con_b.executescript(ddl3)
        con_b.executescript(ddl4)
        con_b.commit()

        rows_b = _sqlite_master_rows(con_b)
    finally:
        con_b.close()

    con_a = sqlite3.connect(db_a)
    try:
        rows_a = _sqlite_master_rows(con_a)
    finally:
        con_a.close()

    assert_schema_equal(rows_a, rows_b)
