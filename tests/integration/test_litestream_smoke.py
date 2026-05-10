"""Litestream replicate → restore smoke (M1.8) — Docker Compose + MinIO."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# Omit hub.override.dev.yml — avoids host port collisions when hub smoke runs in the same
# CI job.
_COMPOSE_PATHS = (
    REPO_ROOT / "deploy/compose/hub.yml",
    REPO_ROOT / "deploy/compose/hub.override.ci.yml",
    REPO_ROOT / "deploy/compose/hub.override.litestream-ci.yml",
)


def _compose_ok() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            capture_output=True,
            timeout=15,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _compose_argv(project: str) -> list[str]:
    cmd = ["docker", "compose", "-p", project]
    for path in _COMPOSE_PATHS:
        cmd.extend(["-f", str(path)])
    return cmd


@pytest.fixture(scope="module")
def litestream_hub_stack_module() -> str:
    project_id = f"ti_litestream_{uuid.uuid4().hex[:10]}"
    argv = _compose_argv(project_id)
    env = {**os.environ, "COMPOSE_PROFILES": "minimal,litestream"}
    up = [*argv, "up", "-d", "--build", "--wait", "--wait-timeout", "300"]
    down = [*argv, "down", "-v", "--remove-orphans"]

    proc = subprocess.run(
        up,
        cwd=REPO_ROOT,
        check=False,
        timeout=420,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"docker compose up failed:\n{proc.stdout}\n{proc.stderr}",
        )
    try:
        yield project_id
    finally:
        subprocess.run(down, cwd=REPO_ROOT, capture_output=True, timeout=240, check=False)


def _volume_name(project_id: str) -> str:
    return f"{project_id}_hub_db_data"


def _seed_sqlite(project_id: str) -> None:
    vol = _volume_name(project_id)
    script = (
        "apk add --no-cache sqlite >/dev/null && "
        "sqlite3 /data/terra.sqlite 'CREATE TABLE IF NOT EXISTS smoke(id INTEGER PRIMARY KEY);' && "
        "sqlite3 /data/terra.sqlite 'INSERT INTO smoke(id) VALUES (42);' && "
        "sqlite3 /data/terra.sqlite 'PRAGMA wal_checkpoint(TRUNCATE);'"
    )
    subprocess.run(
        ["docker", "run", "--rm", "-v", f"{vol}:/data", "alpine:3.20", "sh", "-c", script],
        cwd=REPO_ROOT,
        check=True,
        timeout=120,
    )


def test_retention_policy_set() -> None:
    cfg_path = REPO_ROOT / "deploy/litestream/config.yml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    dbs = data.get("dbs", [])
    assert dbs, "expected dbs entry"
    assert dbs[0].get("min-checkpoint-page-count") == 1024
    replicas = dbs[0].get("replicas", [])
    assert replicas
    assert replicas[0].get("retention") == "720h"
    assert replicas[0].get("validation-interval") == "12h"


@pytest.mark.compose_litestream
@pytest.mark.skipif(not _compose_ok(), reason="Docker Compose v2 not available")
def test_replicate_and_restore(litestream_hub_stack_module: str) -> None:
    project_id = litestream_hub_stack_module
    _seed_sqlite(project_id)
    argv = _compose_argv(project_id)
    env = {**os.environ, "COMPOSE_PROFILES": "minimal,litestream"}
    # config.ci.yml uses aggressive checkpoints; allow replicate to flush generations.
    time.sleep(35)

    subprocess.run(
        [
            *argv,
            "exec",
            "-T",
            "litestream",
            "litestream",
            "restore",
            "-parallelism",
            "2",
            "-config",
            "/etc/litestream.yml",
            "-o",
            "/var/lib/terra/db/restored.sqlite",
            "/var/lib/terra/db/terra.sqlite",
        ],
        cwd=REPO_ROOT,
        check=True,
        timeout=240,
        env=env,
    )

    vol = _volume_name(project_id)
    verify_sh = (
        "apk add --no-cache sqlite >/dev/null && "
        "sqlite3 /data/restored.sqlite 'SELECT id FROM smoke WHERE id=42;'"
    )
    proc = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{vol}:/data",
            "alpine:3.20",
            "sh",
            "-c",
            verify_sh,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert proc.stdout.strip() == "42"
