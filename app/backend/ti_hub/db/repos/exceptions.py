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
