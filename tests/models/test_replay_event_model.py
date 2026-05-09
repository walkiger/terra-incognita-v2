"""M1.6 — ``ReplayEvent`` Pydantic model."""

from __future__ import annotations

from typing import Any, cast

import pytest
from models import (
    ReplayEvent,
    ReplayEventDraft,
    ReplayItem,
    ReplayScoreWeights,
    ReplayWindowRequest,
    ReplayWindowResponse,
)
from pydantic import ValidationError


def test_replay_event_draft_round_trip() -> None:
    draft = ReplayEventDraft(ts=10, kind="encounter", payload={"word": "moon"})
    assert draft.ts == 10
    assert draft.kind == "encounter"
    assert draft.payload == {"word": "moon"}
    assert draft.schema_ver == 1


def test_replay_event_full_row() -> None:
    ev = ReplayEvent(
        id=1,
        user_id=2,
        ts=100,
        kind="encounter",
        payload={"k": 1},
        schema_ver=1,
    )
    assert ev.id == 1 and ev.user_id == 2


def test_score_weights_bounds() -> None:
    ReplayScoreWeights(bm25=0.0, substring=0.0)
    ReplayScoreWeights(bm25=1.0, substring=1.0)
    with pytest.raises(ValidationError):
        ReplayScoreWeights(bm25=-0.01, substring=0.5)
    with pytest.raises(ValidationError):
        ReplayScoreWeights(bm25=1.01, substring=0.5)


def test_window_request_defaults() -> None:
    req = ReplayWindowRequest()
    assert req.limit == 100
    assert req.ranking_mode == "chronological"
    assert req.score_weights.bm25 == 0.5
    assert req.score_weights.substring == 0.5


def test_window_request_limit_max_enforced() -> None:
    ReplayWindowRequest(limit=500)
    with pytest.raises(ValidationError):
        ReplayWindowRequest(limit=501)


def test_window_request_q_max_length() -> None:
    ReplayWindowRequest(q="a" * 128)
    with pytest.raises(ValidationError):
        ReplayWindowRequest(q="a" * 129)


def test_window_response_schema_version_pinned() -> None:
    resp = ReplayWindowResponse(
        items=[],
        truncated=False,
        next_after_id=None,
        effective_policy=None,
        score_weights=ReplayScoreWeights(),
    )
    assert resp.schema_version == "replay_timeline_window_v4"


def test_window_response_rejects_other_schema_version() -> None:
    with pytest.raises(ValidationError):
        ReplayWindowResponse(
            schema_version=cast(Any, "replay_timeline_window_v3"),
            items=[],
            truncated=False,
            next_after_id=None,
            effective_policy=None,
            score_weights=ReplayScoreWeights(),
        )


def test_replay_item_score_optional() -> None:
    ev = ReplayEvent(id=1, user_id=2, ts=0, kind="t", payload={}, schema_ver=1)
    chrono = ReplayItem(event=ev, score=None)
    hybrid = ReplayItem(event=ev, score=0.42)
    assert chrono.score is None
    assert hybrid.score == pytest.approx(0.42)
