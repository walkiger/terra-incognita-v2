"""Compose hub smoke (M0.3) — requires Docker Compose v2."""

from __future__ import annotations

import json
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
    pytest.mark.compose_hub,
    pytest.mark.skipif(not _compose_ok(), reason="Docker Compose v2 not available"),
]


def _compose_argv(project: str) -> list[str]:
    cmd = ["docker", "compose", "-p", project]
    for path in _COMPOSE_PATHS:
        cmd.extend(["-f", str(path)])
    return cmd


@pytest.fixture(scope="module")
def minimal_hub_stack_module() -> str:
    project_id = f"ti_hub_m03_{uuid.uuid4().hex[:10]}"
    argv = _compose_argv(project_id)
    up = [*argv, "--profile", "minimal", "up", "-d", "--build", "--wait", "--wait-timeout", "240"]
    down = [*argv, "--profile", "minimal", "down", "-v", "--remove-orphans"]

    subprocess.run(up, cwd=REPO_ROOT, check=True, timeout=300)
    try:
        yield project_id
    finally:
        subprocess.run(down, cwd=REPO_ROOT, capture_output=True, timeout=180, check=False)


def test_compose_minimal_brings_up(minimal_hub_stack_module: str) -> None:
    argv = _compose_argv(minimal_hub_stack_module)
    proc = subprocess.run(
        [*argv, "--profile", "minimal", "ps", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    ids = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(ids) >= 4


@pytest.mark.usefixtures("minimal_hub_stack_module")
def test_health_endpoint_through_caddy() -> None:
    with urlopen("http://127.0.0.1:8080/v1/health", timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload == {"ok": True, "version": "0.0.1-bootstrap"}
