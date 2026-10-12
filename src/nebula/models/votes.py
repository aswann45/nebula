"""Canonical roll-call fields shared where available."""

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VoteRecord(BaseModel):
    """A roll-call summary with a source-specific result string."""

    model_config = ConfigDict(frozen=True)

    source: str
    chamber: Literal["House", "Senate"]
    year: int = Field(ge=1789)
    roll_call_number: int = Field(gt=0)
    action_date: date
    result: str


class VotePosition(StrEnum):
    """Common normalized positions for recorded votes."""

    YEA = "yea"
    NAY = "nay"
    PRESENT = "present"
    NOT_VOTING = "not_voting"
    OTHER = "other"


def normalize_vote_position(value: str) -> VotePosition:
    """Map known House position labels without discarding the source text."""
    normalized = value.strip().lower()
    if normalized in {"yea", "aye", "yes"}:
        return VotePosition.YEA
    if normalized in {"nay", "no"}:
        return VotePosition.NAY
    if normalized == "present":
        return VotePosition.PRESENT
    if normalized in {"not voting", "not-voting"}:
        return VotePosition.NOT_VOTING
    return VotePosition.OTHER
