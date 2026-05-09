"""Defaults for Hub SQLite subsystems (M1+)."""

from __future__ import annotations

from typing import Final

# Debounce window after the last append signal before a full FTS rebuild is considered (seconds).
REPLAY_FTS_REBUILD_DEBOUNCE_S: Final[float] = 30.0
