"""Hub compose default profile — Prometheus + Grafana (M0.9)."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from urllib.request import urlopen

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_COMPOSE_PATHS = (
    REPO_ROOT / "deploy/compose/hub.yml",
    REPO_ROOT / "deploy/compose/hub.override.ci.yml",
    REPO_ROOT / "deploy/compose/hub.override.dev.yml",
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


pytestmark = [
    pytest.mark.compose_observability,
    pytest.mark.skipif(not _compose_ok(), reason="Docker Compose v2 not available"),
]


def _compose_argv(project: str) -> list[str]:
    cmd = ["docker", "compose", "-p", project]
    for path in _COMPOSE_PATHS:
        cmd.extend(["-f", str(path)])
    return cmd


@pytest.fixture(scope="module")
def default_hub_stack_module() -> str:
    project_id = f"ti_hub_obs_{uuid.uuid4().hex[:10]}"
    argv = _compose_argv(project_id)
    up = [*argv, "--profile", "default", "up", "-d", "--build", "--wait", "--wait-timeout", "400"]
    down = [*argv, "--profile", "default", "down", "-v", "--remove-orphans"]

    subprocess.run(up, cwd=REPO_ROOT, check=True, timeout=600)
    try:
        yield project_id
    finally:
        subprocess.run(down, cwd=REPO_ROOT, capture_output=True, timeout=240, check=False)


def test_default_profile_brings_obs_stack(default_hub_stack_module: str) -> None:
    argv = _compose_argv(default_hub_stack_module)
    proc = subprocess.run(
        [*argv, "--profile", "default", "ps", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    ids = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(ids) >= 7


@pytest.mark.usefixtures("default_hub_stack_module")
def test_grafana_health_on_loopback() -> None:
    with urlopen("http://127.0.0.1:3002/api/health", timeout=30) as resp:
        assert resp.status == 200


@pytest.mark.usefixtures("default_hub_stack_module")
def test_prometheus_ready_on_loopback() -> None:
    with urlopen("http://127.0.0.1:9091/-/ready", timeout=30) as resp:
        assert resp.status == 200
