"""Hub ``encounters`` rows (M1.5)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EncounterSource = Literal["user_input", "ghost", "walk", "kg_spontaneous", "replay"]


class EncounterDraft(BaseModel):
    """Insert payload for EncountersRepository.append — excludes DB-assigned keys."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    word: str | None = None
    scale: float
    source: EncounterSource
    context: dict[str, Any] = Field(default_factory=dict)


class Encounter(BaseModel):
    """Materialized encounter row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    ts: int = Field(ge=0)
    word: str | None
    scale: float
    source: EncounterSource
    context: dict[str, Any]
