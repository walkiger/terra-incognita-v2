"""strip_cursor_coauthor_trailer hook logic."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_strip():
    path = REPO / "scripts" / "strip_cursor_coauthor_trailer.py"
    spec = importlib.util.spec_from_file_location("strip_trailer_mod", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_removes_trailer_when_present() -> None:
    mod = _load_strip()
    raw = "feat: thing\n\nCo-authored-by: Cursor <cursoragent@cursor.com>\n"
    assert "Co-authored-by" not in mod.strip_trailer(raw)


def test_idempotent_when_absent() -> None:
    mod = _load_strip()
    raw = "feat: thing\n\nSigned-off-by: Dev <dev@example.com>\n"
    assert mod.strip_trailer(raw) == raw
