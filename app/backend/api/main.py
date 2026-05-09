"""Hub API bootstrap — full FastAPI surface arrives in M5.

M5.1 replaces this module with create_app() factory, lifespan hooks,
middleware stack, and proper router registration.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header

from .observability import metrics_response, register_build_info

app = FastAPI(title="terra-incognita hub", version="0.0.1-bootstrap")

register_build_info(app.version)


@app.get("/v1/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": "0.0.1-bootstrap"}


@app.get("/metrics")
def metrics(authorization: str | None = Header(default=None)) -> Any:
    return metrics_response(authorization)
