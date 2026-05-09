"""Hub ``users`` row projections (M1.4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserStatus = Literal["active", "disabled"]


class User(BaseModel):
    """Public user shape — excludes credential hash."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int = Field(gt=0)
    email: EmailStr
    created_at: int = Field(ge=0)
    status: UserStatus
    is_admin: bool


class UserCredentials(BaseModel):
    """Internal insert/update bundle — only repositories should construct this."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: EmailStr
    pwhash_argon2: str = Field(min_length=1)
