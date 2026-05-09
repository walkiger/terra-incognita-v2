"""Hub uvicorn entry point.

M5.1 replaces this with a proper create_app() factory imported from
app/backend/api/app.py.  Until then this re-exports the bootstrap app
so that `uvicorn backend.main:app` works both locally and in the
container (PYTHONPATH=/workspace, WORKDIR=/app).

Container CMD uses `uvicorn api.main:app` directly (shorter import).
This file is the canonical local-dev entry point referenced in M5.1.
"""

from api.main import app  # noqa: F401 — re-export for uvicorn

__all__ = ["app"]
