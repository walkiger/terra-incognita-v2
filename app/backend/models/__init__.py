"""Domain Pydantic v2 models — populated from M1.4 onward.

M1.4: models.user      — User, UserCredentials
M1.5: models.encounter — Encounter, EncounterDraft
M1.6: models.replay_event — ReplayEvent, ReplayWindowResponse
M1.7: models.snapshot  — Snapshot, SnapshotInitiateRequest
"""

from .encounter import Encounter, EncounterDraft, EncounterSource
from .replay_event import (
    ReplayEvent,
    ReplayEventDraft,
    ReplayItem,
    ReplayQMatch,
    ReplayRankingMode,
    ReplayRankingPolicy,
    ReplayScoreWeights,
    ReplayWindowRequest,
    ReplayWindowResponse,
)
from .snapshot import Snapshot, SnapshotInitiateRequest, SnapshotScope, SnapshotStatus
from .user import User, UserCredentials

__all__ = [
    "Encounter",
    "EncounterDraft",
    "EncounterSource",
    "ReplayEvent",
    "ReplayEventDraft",
    "ReplayItem",
    "ReplayQMatch",
    "ReplayRankingMode",
    "ReplayRankingPolicy",
    "ReplayScoreWeights",
    "ReplayWindowRequest",
    "ReplayWindowResponse",
    "Snapshot",
    "SnapshotInitiateRequest",
    "SnapshotScope",
    "SnapshotStatus",
    "User",
    "UserCredentials",
]
