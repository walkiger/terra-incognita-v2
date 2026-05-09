"""FastAPI /metrics bearer gate (M0.9)."""

from __future__ import annotations

import os

from starlette.testclient import TestClient

os.environ["METRICS_BEARER_TOKEN"] = "unit-test-token"

from api.main import app

_CLIENT = TestClient(app)


def test_metrics_endpoint_responds() -> None:
    res = _CLIENT.get("/metrics", headers={"Authorization": "Bearer unit-test-token"})
    assert res.status_code == 200
    assert "terra_hub_build_info" in res.text


def test_metrics_exposes_minimum_set() -> None:
    res = _CLIENT.get("/metrics", headers={"Authorization": "Bearer unit-test-token"})
    assert res.status_code == 200
    assert "0.0.1-bootstrap" in res.text


def test_metrics_rejects_bad_bearer() -> None:
    res = _CLIENT.get("/metrics", headers={"Authorization": "Bearer wrong"})
    assert res.status_code == 401
