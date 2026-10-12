"""Pydantic models for parsing Senate member data from the Clerk XML feed.

These models represent individual Senators, their committee assignments,
state metadata, and name structure. Supports computed name formatting,
office parsing, and state resolution.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

import us
from pydantic import BaseModel, ConfigDict, Field, computed_field


class LastUpdate(BaseModel):
    """Represents the timestamp when the Senate roster was last updated.

    Attributes
    ----------
    date : str
        Date in YYYY-MM-DD format.
    time : str
        Time in HH:MM:SS format.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    date: str
    time: str


class Name(BaseModel):
    """Structured components of a Senator's name.

    Attributes
    ----------
    prefix : str
        Courtesy title (e.g., "Senator").
    first : str
        First name.
    last : str
        Last name.
    suffix : str, optional
        Name suffix (e.g., "Jr.", "III").

    """

    model_config = ConfigDict(
        extra="allow",
    )
    prefix: str
    first: str
    last: str
    suffix: str | None = None


class CommitteeItem(BaseModel):
    """A single Senate committee assignment.

    Attributes
    ----------
    code : str
        Committee code, such as 'SSAF' (Senate Armed Forces).
    text : str
        Committee name (e.g., "Armed Services").
    leadership : str, optional
        Display leadership title (e.g., "Chair").
    parsed_leadership : str, optional
        Inferred or mapped leadership role.
    type : str
        Static literal string, always set to 'Committee'.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    code: Annotated[str, Field(alias="@code")]
    text: Annotated[str, Field(alias="#text")]
    leadership: Annotated[str | None, Field(alias="@position")] = None
    parsed_leadership: Annotated[str | None, Field(alias="@position")] = None
    type: str = "Committee"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chamber_id(self) -> str:
        """Return committee code without chamber prefix.

        For example, from 'SSAF' → 'AF'.

        Returns
        -------
        str
            Committee-specific identifier string.

        """
        return self.code[2:]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_rank(self) -> int:
        """Return rank based on presence of a leadership title.

        Returns 1 if `parsed_leadership` exists, else 0.

        Returns
        -------
        int
            Inferred rank value.

        """
        if self.parsed_leadership is not None:
            return 1
        else:
            return 0


class CommitteeAssignments(BaseModel):
    """Collection of Senate committee assignments for one Senator.

    Attributes
    ----------
    committee : list[CommitteeItem]
        List of committees the Senator serves on.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    committee: Sequence[CommitteeItem]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_assignments(self) -> Sequence[CommitteeItem]:
        """Return list of all committee assignments.

        Useful for interface consistency with House models.

        Returns
        -------
        list[CommitteeItem]
            Full committee assignment list.

        """
        return self.committee


class SenatorItem(BaseModel):
    """Model for a single U.S. Senator's metadata and assignments.

    Attributes
    ----------
    bioguide_id : str
        Unique identifier in the Bioguide system.
    name : Name
        Structured name components.
    parsed_predecessor_info : None
        Always None in the Senate schema (for compatibility).
    party : str
        Party affiliation (e.g., "R", "D").
    state_postal_code : str
        Two-letter state code (e.g., "TX").
    town_name : str
        Hometown of the Senator.
    state_rank : str
        Indicates seniority within the state (e.g., "Senior").
    office : str
        Raw office location string (e.g., "B33 Russell").
    committee_assignments : CommitteeAssignments
        Senate committee assignments.
    field_lis_member_id : str
        LIS-specific identifier used by the Senate.
    leadership_position : str, optional
        Chamber-wide leadership role (e.g., "Majority Leader").
    chamber : str
        Always "Senate".

    """

    model_config = ConfigDict(
        extra="allow",
    )
    bioguide_id: Annotated[str, Field(alias="bioguideId")]
    name: Name
    parsed_predecessor_info: None = Field(default=None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def lastname(self) -> str:
        """Return the Senator's last name."""
        return self.name.last

    @computed_field  # type: ignore[prop-decorator]
    @property
    def firstname(self) -> str:
        """Return the Senator's first name."""
        return self.name.first

    @computed_field  # type: ignore[prop-decorator]
    @property
    def namelist(self) -> str:
        """Return formatted name as 'Last, First'."""
        return f"{self.lastname}, {self.firstname}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def suffix(self) -> str | None:
        """Return suffix from the name block, if present."""
        return self.name.suffix

    @computed_field  # type: ignore[prop-decorator]
    @property
    def courtesy(self) -> str:
        """Return title or courtesy prefix from the name block."""
        return self.name.prefix

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sort_name(self) -> str:
        """Return all-uppercase 'Last, First' for sorting."""
        return self.namelist.upper()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def official_name(self) -> str:
        """Return 'First Last' name format."""
        return f"{self.firstname} {self.lastname}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def formal_name(self) -> str:
        """Return formatted name with courtesy prefix."""
        return f"{self.courtesy} {self.official_name}"

    party: str
    state_postal_code: Annotated[str, Field(alias="state")]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def state_fullname(self) -> str:
        """Return full U.S. state name from postal code."""
        try:
            return us.states.lookup(self.state_postal_code).name  # type: ignore[union-attr]
        except AttributeError as ae:
            raise ValueError(
                f"Could not resolve state name from {self.state_postal_code}"
            ) from ae

    town_name: Annotated[str, Field(alias="homeTown")]
    state_rank: Annotated[str, Field(alias="stateRank")]
    office: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def office_building(self) -> str:
        """Return Senate office building from the `office` string."""
        return self.office.split(" ")[1]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def office_room(self) -> str:
        """Return Senate office room number from the `office` string."""
        return self.office.split(" ")[0]

    committee_assignments: Annotated[
        CommitteeAssignments, Field(alias="committees")
    ]
    field_lis_member_id: Annotated[str, Field(alias="@lis_member_id")]
    leadership_position: str | None = None
    chamber: str = "Senate"


class Senators(BaseModel):
    """Wrapper for full Senate roster as published by the Clerk.

    Attributes
    ----------
    last_update : LastUpdate
        Timestamp of last data refresh.
    member : list[SenatorItem]
        List of currently serving Senators.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    last_update: Annotated[LastUpdate, Field(alias="lastUpdate")]
    member: Annotated[Sequence[SenatorItem], Field(alias="senator")]


class SenatorsData(BaseModel):
    """Top-level container for parsed Senate roster response.

    Attributes
    ----------
    members : Senators
        Wrapped list of Senators and update metadata.

    """

    members: Senators


class ClerkData(BaseModel):
    """Parsed top-level schema for Clerk of the Senate dataset.

    Attributes
    ----------
    senators : Senators
        Full Senate membership block.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    senators: Senators

    @computed_field  # type: ignore[prop-decorator]
    @property
    def data(self) -> SenatorsData:
        """Return top-level data container with structured members.

        Returns
        -------
        SenatorsData
            Root object containing Senators and metadata.

        """
        return SenatorsData(members=self.senators)
