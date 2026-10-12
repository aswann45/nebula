"""Canonical member fields shared where source evidence permits."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MemberRecord(BaseModel):
    """A minimal normalized identity for a congressional member."""

    model_config = ConfigDict(frozen=True)

    source: str
    bioguide_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    chamber: Literal["House", "Senate"] | None = None
    state: str | None = None
