"""Snapshot domain models (M1.7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SnapshotScope = Literal["full", "incremental"]
SnapshotStatus = Literal["uploading", "ready", "expired"]

_MAX_SIZE_BYTES = 64 * 1024 * 1024  # 64 MB hard limit


class SnapshotInitiateRequest(BaseModel):
    """Payload to start a new snapshot upload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: SnapshotScope
    expected_size_bytes: int = Field(ge=1, le=_MAX_SIZE_BYTES)
    content_sha256: str = Field(min_length=64, max_length=64)


class Snapshot(BaseModel):
    """Materialized ``snapshots`` row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int
    user_id: int
    ts: int
    scope: SnapshotScope
    size_bytes: int
    content_sha256: str
    r2_key: str
    status: SnapshotStatus
