"""FastAPI /metrics bearer gate (M0.9)."""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

os.environ["METRICS_BEARER_TOKEN"] = "unit-test-token"

from api.main import app


@pytest.fixture
def metrics_client() -> TestClient:
    # scope="function": TestClient torn down while the function event-loop is
    # still active, letting anyio (Starlette 0.4x) shut down its ASGI thread
    # cleanly.  scope="module" caused a 10-minute hang on Linux: the anyio
    # cleanup ran after pytest-asyncio closed all event loops.
    with TestClient(app) as client:
        yield client


def test_metrics_endpoint_responds(metrics_client: TestClient) -> None:
    res = metrics_client.get("/metrics", headers={"Authorization": "Bearer unit-test-token"})
    assert res.status_code == 200
    assert "terra_hub_build_info" in res.text


def test_metrics_exposes_minimum_set(metrics_client: TestClient) -> None:
    res = metrics_client.get("/metrics", headers={"Authorization": "Bearer unit-test-token"})
    assert res.status_code == 200
    assert "0.0.1-bootstrap" in res.text


def test_metrics_rejects_bad_bearer(metrics_client: TestClient) -> None:
    res = metrics_client.get("/metrics", headers={"Authorization": "Bearer wrong"})
    assert res.status_code == 401
