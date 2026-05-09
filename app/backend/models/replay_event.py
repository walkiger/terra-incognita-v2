"""Hub ``replay_events`` rows + window query types (M1.6).

Mirrors the legacy `replay_timeline_window_v4` contract (terra-076..082) so
that M5.8 can pass these straight through to the HTTP layer.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ReplayQMatch = Literal["substring", "fts"]
ReplayRankingMode = Literal["chronological", "hybrid"]
ReplayRankingPolicy = Literal["bm25_only", "substring_only", "combined"]


class ReplayEventDraft(BaseModel):
    """Append payload — excludes DB-assigned id and the tenant-injected user_id."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ts: int = Field(ge=0)
    kind: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_ver: int = Field(gt=0, default=1)


class ReplayEvent(BaseModel):
    """Materialized ``replay_events`` row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    ts: int = Field(ge=0)
    kind: str
    payload: dict[str, Any]
    schema_ver: int = Field(gt=0)


class ReplayScoreWeights(BaseModel):
    """α / β for the hybrid combined-policy score (terra-080).

    Returned in :class:`ReplayWindowResponse` so M5.8 can echo the *effective*
    weights back to clients alongside ``effective_policy``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    bm25: float = Field(ge=0.0, le=1.0, default=0.5)
    substring: float = Field(ge=0.0, le=1.0, default=0.5)


class ReplayWindowRequest(BaseModel):
    """One page request — chronological cursor or hybrid score window."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    limit: int = Field(gt=0, le=500, default=100)
    after_id: int | None = Field(default=None, ge=0)
    since_ts: int | None = Field(default=None, ge=0)
    until_ts: int | None = Field(default=None, ge=0)
    kind: str | None = None
    q: str | None = Field(default=None, max_length=128)
    q_match: ReplayQMatch | None = None
    ranking_mode: ReplayRankingMode = "chronological"
    ranking_policy: ReplayRankingPolicy | None = None
    score_weights: ReplayScoreWeights = Field(default_factory=ReplayScoreWeights)


class ReplayItem(BaseModel):
    """One row in :class:`ReplayWindowResponse`. ``score`` is ``None`` for chronological."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event: ReplayEvent
    score: float | None


class ReplayWindowResponse(BaseModel):
    """``replay_timeline_window_v4`` materialisation. ``next_after_id`` is ``None`` for hybrid."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["replay_timeline_window_v4"] = "replay_timeline_window_v4"
    items: list[ReplayItem]
    truncated: bool
    next_after_id: int | None
    effective_policy: ReplayRankingPolicy | None
    score_weights: ReplayScoreWeights
