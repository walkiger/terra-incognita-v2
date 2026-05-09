"""Protected deletion gate helpers."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _subprocess_env() -> dict[str, str]:
    """Strip Actions-only vars so the script uses staged-diff mode in temp repos."""
    banned = {"GITHUB_ACTIONS", "GITHUB_BASE_REF"}
    return {k: v for k, v in os.environ.items() if k not in banned}


def _load_cpd():
    path = REPO / "scripts" / "check_protected_deletions.py"
    spec = importlib.util.spec_from_file_location("cpd", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_is_protected_memory_prefix() -> None:
    mod = _load_cpd()
    assert mod.is_protected("memory/system/decisions.md")


def test_is_protected_not_docs() -> None:
    mod = _load_cpd()
    assert not mod.is_protected("tmp/foo.txt")


def test_blocks_unapproved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.name", "t"], check=True, capture_output=True)
    d = tmp_path / "docs"
    d.mkdir()
    p = d / "probe.md"
    p.write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "docs/probe.md"], check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], check=True, capture_output=True)
    p.unlink()
    subprocess.run(["git", "add", "-u"], check=True, capture_output=True)
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_protected_deletions.py")],
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    assert proc.returncode == 1


def test_allows_when_no_deletions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], check=True, capture_output=True)
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_protected_deletions.py")],
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    assert proc.returncode == 0
