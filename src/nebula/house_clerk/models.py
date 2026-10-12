"""Typed records for House Clerk roll-call votes."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from nebula.models.votes import VotePosition, normalize_vote_position


class HouseRecordedVote(BaseModel):
    """A House member's recorded position on a roll call."""

    model_config = ConfigDict(extra="allow")

    bioguide_id: str
    vote: str
    party: str | None = None
    member_last_name: str | None = None
    source_record: dict[str, JsonValue] = Field(default_factory=dict)

    @property
    def normalized_position(self) -> VotePosition:
        """Map the published label to a common position when known."""
        return normalize_vote_position(self.vote)


class HouseRollCall(BaseModel):
    """Validated vote metadata and member positions."""

    model_config = ConfigDict(extra="allow")

    congress: int
    session: str
    chamber: str = "House"
    roll_call_number: int
    bill_number: str | None = None
    vote_question: str
    vote_description: str | None = None
    vote_type: str
    vote_result: str
    action_date: date
    majority: str | None = None
    amendment_author: str | None = None
    amendment_number_offered: int | None = None
    year: int
    votes: list[HouseRecordedVote] = Field(default_factory=list)
    source_metadata: dict[str, JsonValue] = Field(default_factory=dict)


class HouseRollCallRequest(BaseModel):
    """Validated identifiers for one House roll-call request."""

    year: int = Field(ge=1789)
    roll_call_number: int = Field(gt=0)
