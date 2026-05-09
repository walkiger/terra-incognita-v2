"""M0.2 — pyproject / uv / ruff / mypy wiring assertions."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pyproject_data() -> dict:
    import tomllib

    raw = (REPO_ROOT / "pyproject.toml").read_bytes()
    return tomllib.loads(raw.decode("utf-8"))


def test_pyproject_python_constraint(pyproject_data: dict) -> None:
    req = pyproject_data["project"]["requires-python"]
    assert ">=3.12" in req
    assert "<3.13" in req


def test_ruff_config_present(pyproject_data: dict) -> None:
    assert "tool" in pyproject_data
    assert "ruff" in pyproject_data["tool"]
    assert pyproject_data["tool"]["ruff"].get("target-version") == "py312"


def test_mypy_strict_config_present(pyproject_data: dict) -> None:
    mypy = pyproject_data["tool"]["mypy"]
    assert mypy.get("strict") is True
    assert mypy.get("python_version") == "3.12"


def test_uv_lock_committed() -> None:
    lock = REPO_ROOT / "uv.lock"
    assert lock.is_file(), "uv.lock must be committed (run `uv lock`)"
