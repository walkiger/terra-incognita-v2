"""Vault r2-pull integration against MinIO + Litestream writer stack (M1.10)."""

from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_COMPOSE_PATHS = (REPO_ROOT / "deploy/compose/r2-pull.integration-ci.yml",)


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


pytestmark = [
    pytest.mark.compose_r2_pull,
    pytest.mark.skipif(not _compose_ok(), reason="Docker Compose v2 not available"),
]


def _compose_argv(project: str) -> list[str]:
    cmd = ["docker", "compose", "-p", project]
    for path in _COMPOSE_PATHS:
        cmd.extend(["-f", str(path)])
    return cmd


@pytest.fixture(scope="module")
def r2_sync_stack_module() -> str:
    project_id = f"ti_r2pull_{uuid.uuid4().hex[:10]}"
    argv = _compose_argv(project_id)
    up = [*argv, "up", "-d", "--build", "--wait", "--wait-timeout", "300"]
    down = [*argv, "down", "-v", "--remove-orphans"]

    subprocess.run(up, cwd=REPO_ROOT, check=True, timeout=420)
    try:
        yield project_id
    finally:
        subprocess.run(down, cwd=REPO_ROOT, capture_output=True, timeout=240, check=False)


def _vault_vol(project_id: str) -> str:
    return f"{project_id}_vault_demo_db"


def _hub_vol(project_id: str) -> str:
    return f"{project_id}_hub_demo_db"


def _run_sql(vol: str, dbfile: str, shell_fragment: str) -> str:
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
            (f"apk add --no-cache sqlite >/dev/null && sqlite3 /data/{dbfile} {shell_fragment}"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return proc.stdout.strip()


def test_pulls_initial_replica(r2_sync_stack_module: str) -> None:
    time.sleep(45)
    out = _run_sql(
        _vault_vol(r2_sync_stack_module), "terra.sqlite", "'SELECT id FROM smoke WHERE id=42;'"
    )
    assert out == "42"


def test_subsequent_changes_propagate(r2_sync_stack_module: str) -> None:
    hub_vol = _hub_vol(r2_sync_stack_module)
    _run_sql(hub_vol, "terra.sqlite", "'INSERT INTO smoke(id) VALUES (99);'")
    _run_sql(hub_vol, "terra.sqlite", "'PRAGMA wal_checkpoint(TRUNCATE);'")
    time.sleep(45)
    out = _run_sql(
        _vault_vol(r2_sync_stack_module), "terra.sqlite", "'SELECT id FROM smoke WHERE id=99;'"
    )
    assert out == "99"


def test_metrics_exposed(r2_sync_stack_module: str) -> None:
    argv = _compose_argv(r2_sync_stack_module)
    proc = subprocess.run(
        [
            *argv,
            "exec",
            "-T",
            "r2_pull_worker",
            "python",
            "-c",
            "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8081/metrics').read().decode())",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert "vault_litestream_restore_success_total" in proc.stdout
