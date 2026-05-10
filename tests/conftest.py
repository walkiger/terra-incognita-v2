"""Session-level test fixtures and patches."""

from __future__ import annotations

import threading

import aiosqlite.core as _aiosqlite_core

# aiosqlite worker threads are non-daemon by default.  Non-daemon threads
# block Python's interpreter shutdown: pytest-asyncio 1.x changed GC timing
# so thread __del__ cleanup no longer runs before the thread-join phase.
# Making the threads daemon lets Python exit freely; the OS reaps them.
# This only affects `:memory:` databases used in the test suite.
_original_Thread = _aiosqlite_core.Thread


def _daemon_thread(*args, **kwargs) -> threading.Thread:  # type: ignore[return]
    t = _original_Thread(*args, **kwargs)
    t.daemon = True
    return t


_aiosqlite_core.Thread = _daemon_thread  # type: ignore[assignment]
