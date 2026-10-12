"""Legacy typed dictionaries retained for source-client compatibility."""

from typing import Any, TypedDict

MemberInfoDict = dict[str, Any]


class RollCallYears(TypedDict):
    """Helper structure for year + roll call numbers."""

    year: int
    roll_call_numbers: int | list[int]


class RollCallParams(TypedDict):
    """Search parameters for roll call fetch/insertion."""

    years: int | list[int | RollCallYears]


class RollCallRequestParams(TypedDict):
    """Helper class for pulling roll call data."""

    year: str | int
    roll_call_number: str | int


RollCallDict = dict[str, Any]
"""Generic roll call vote record."""

VoteMeta = dict[str, Any]
"""Vote metadata from clerk.house.gov."""

RecordedVote = dict[str, str]
"""Individual vote by member ID."""
