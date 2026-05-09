"""Prometheus metrics wiring for Hub API (M0.9 bootstrap; full instrumentation in M5)."""

from __future__ import annotations

import os

from prometheus_client import CONTENT_TYPE_LATEST, Info, generate_latest
from starlette.responses import Response

_BUILD = Info(
    "terra_hub_build",
    "Hub container build metadata (stub until full Prom instrumentation in M5).",
)


def register_build_info(version: str) -> None:
    _BUILD.info({"version": version})


def metrics_response(authorization: str | None) -> Response:
    expected = os.environ.get("METRICS_BEARER_TOKEN", "").strip()
    if not expected:
        return Response("metrics disabled\n", status_code=503, media_type="text/plain")
    got = (authorization or "").strip()
    if got != f"Bearer {expected}":
        return Response("unauthorized\n", status_code=401, media_type="text/plain")
    payload = generate_latest()
    return Response(payload, media_type=CONTENT_TYPE_LATEST)
