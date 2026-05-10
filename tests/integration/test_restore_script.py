"""Restore hub script smoke (M1.11)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_full_restore_flow() -> None:
    if shutil.which("bash") is None:
        pytest.skip("bash not available")
    script = REPO_ROOT / "scripts" / "operations" / "restore_hub.sh"
    assert script.is_file()
    subprocess.run(["bash", "-n", str(script)], cwd=REPO_ROOT, check=True)
    env = {**os.environ, "RESTORE_HUB_DRY_RUN": "1"}
    subprocess.run(["bash", str(script)], cwd=REPO_ROOT, env=env, check=True)
