"""Repository-layer exceptions."""

from __future__ import annotations

import sqlite3


class RepositoryError(Exception):
    """Domain-facing persistence failure (constraint breach other than duplicate email)."""


class EmailAlreadyRegistered(RepositoryError):
    """Raised when ``users.email`` UNIQUE clause rejects an insert."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"email already registered: {email}")


class SnapshotTooLargeError(RepositoryError):
    """Raised when ``expected_size_bytes`` exceeds the 64 MB hard limit."""

    def __init__(self, size_bytes: int, limit: int) -> None:
        self.size_bytes = size_bytes
        self.limit = limit
        super().__init__(f"snapshot size {size_bytes} exceeds limit {limit}")


class IllegalSnapshotStateError(RepositoryError):
    """Raised when a state transition is not allowed by the snapshot lifecycle."""

    def __init__(self, snapshot_id: int, current: str, attempted: str) -> None:
        self.snapshot_id = snapshot_id
        self.current = current
        self.attempted = attempted
        super().__init__(
            f"snapshot {snapshot_id}: cannot transition from '{current}' via '{attempted}'"
        )


def raise_repository_integrity(
    exc: sqlite3.IntegrityError,
    *,
    context_email: str | None = None,
) -> None:
    """Map ``IntegrityError`` to typed repo exceptions."""

    msg = str(exc).lower()
    if "unique" in msg and "users.email" in msg and context_email is not None:
        raise EmailAlreadyRegistered(context_email) from exc
    raise RepositoryError(str(exc)) from exc
