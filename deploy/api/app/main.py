"""M0.3 hub API stub — full FastAPI surface arrives in M5."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

app = FastAPI(title="terra-incognita hub", version="0.0.1-bootstrap")


@app.get("/v1/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": "0.0.1-bootstrap"}
