"""Canonical committee fields shared by congressional sources."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CommitteeRecord(BaseModel):
    """A minimal normalized committee identity."""

    model_config = ConfigDict(frozen=True)

    source: str
    name: str = Field(min_length=1)
    chamber: Literal["House", "Senate"] | None = None
    source_id: str | None = None
