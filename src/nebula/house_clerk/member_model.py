"""Pydantic models for parsing official Clerk of the House member data.

These models support parsing the full YAML data file used by the Clerk's
office for member rosters, committee and subcommittee assignments, and
predecessor metadata. All date fields, codes, and leadership roles are
normalized into structured types.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TitleInfo(BaseModel):
    """Metadata about the current Congress from the header block.

    Attributes
    ----------
    congress_num : str
        Numerical identifier (e.g., "118").
    congress_text : str
        Full text (e.g., "118th Congress").
    session : str
        Session indicator ("1st", "2nd").
    majority : str
        Majority party name.
    minority : str
        Minority party name.
    clerk : str
        Clerk of the House.
    weburl : str
        Official Clerk site URL.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    congress_num: Annotated[str, Field(alias="congress-num")]
    congress_text: Annotated[str, Field(alias="congress-text")]
    session: str
    majority: str
    minority: str
    clerk: str
    weburl: str


class State(BaseModel):
    """State metadata for a Member or predecessor.

    Attributes
    ----------
    postal_code : str
        Two-letter postal abbreviation.
    state_fullname : str
        Full state name (e.g., "Virginia").

    """

    model_config = ConfigDict(
        extra="allow",
    )
    postal_code: Annotated[str, Field(alias="postal-code")]
    state_fullname: Annotated[str, Field(alias="state-fullname")]


class ElectedDate(BaseModel):
    """Elected date field for a Member.

    Attributes
    ----------
    date : str
        Compact date string (e.g., "20221108").
    text : str, optional
        Human-readable version of the date.

    Computed Properties
    -------------------
    parsed_date : datetime or None
        Parsed datetime object if format is valid.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    date: str
    text: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_date(self) -> datetime | None:
        """Return the election date as a parsed datetime object.

        Attempts to convert the compact string date (formatted as `YYYYMMDD`)
        into a Python `datetime` object. If parsing fails due to an invalid
        or missing value, returns `None`.

        Returns
        -------
        datetime or None
            Parsed `datetime` representation of the election date, or `None`
            if the input string is invalid.

        """
        try:
            return datetime.strptime(self.date, "%Y%m%d")  # Member date format
        except ValueError:
            return None


class SwornDate(ElectedDate):
    """Inherits from ElectedDate."""

    pass


class MemberInfoBase(BaseModel):
    """Core identifying and contact info for a Member.

    Used both independently and embedded in `MemberItem`.

    Attributes
    ----------
    bioguide_id : str, optional
        Bioguide ID (unique Member identifier).
    namelist : str, optional
        "Last, First" formatted name.
    lastname : str, optional
        Last name.
    firstname : str, optional
        First name.
    ...
    elected_date_data : ElectedDate
        Raw date field model.
    sworn_date_data : SwornDate
        Raw date field model.
    ...
    chamber : str
        Always "House" in this schema.

    Computed Properties
    -------------------
    elected_date : datetime or None
    sworn_date : datetime or None
    state_postal_code : str
    state_fullname : str

    """

    model_config = ConfigDict(
        extra="allow",
    )
    bioguide_id: Annotated[str | None, Field(alias="bioguideID")] = None
    namelist: str | None = None
    lastname: str | None = None
    firstname: str | None = None
    middlename: str | None = None
    sort_name: Annotated[str | None, Field(alias="sort-name")] = None
    suffix: str | None = None
    courtesy: str | None = None
    prior_congress: Annotated[str, Field(alias="prior-congress")]
    official_name: Annotated[str | None, Field(alias="official-name")] = None
    formal_name: Annotated[str | None, Field(alias="formal-name")] = None
    party: str | None = None
    caucus: str | None = None
    state: State
    district: str
    town_name: Annotated[str | None, Field(alias="townname")] = None
    office_building: Annotated[str, Field(alias="office-building")]
    office_room: Annotated[str, Field(alias="office-room")]
    office_zip: Annotated[str, Field(alias="office-zip")]
    office_zip_suffix: Annotated[str, Field(alias="office-zip-suffix")]
    phone: str
    elected_date_data: Annotated[ElectedDate, Field(alias="elected-date")]
    sworn_date_data: Annotated[SwornDate, Field(alias="sworn-date")]
    footnote_ref: Annotated[str | None, Field(alias="footnote-ref")] = None
    footnote: str | None = None
    chamber: str = "House"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def elected_date(self) -> datetime | None:
        """Return the Member's elected date as a datetime object.

        Converts the raw string date in `elected_date_data` to a
        Python `datetime` object, if valid.

        Returns
        -------
        datetime or None
            Parsed election date, or `None` if parsing fails.

        """
        return self.elected_date_data.parsed_date

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sworn_date(self) -> datetime | None:
        """Return the date the Member was sworn into office.

        Converts `sworn_date_data` to a `datetime` object using standard
        Clerk format (YYYYMMDD).

        Returns
        -------
        datetime or None
            Parsed swearing-in date, or `None` if invalid.

        """
        return self.sworn_date_data.parsed_date

    @computed_field  # type: ignore[prop-decorator]
    @property
    def state_postal_code(self) -> str:
        """Return the two-letter postal abbreviation for the Member's state.

        Returns
        -------
        str
            State postal abbreviation (e.g., "CA", "TX").

        """
        return self.state.postal_code

    @computed_field  # type: ignore[prop-decorator]
    @property
    def state_fullname(self) -> str:
        """Return the full name of the Member's state.

        Returns
        -------
        str
            Full state name (e.g., "California", "Texas").

        """
        return self.state.state_fullname


class MemberInfo(MemberInfoBase):
    """Extended model for parsed members with state-district key.

    Attributes
    ----------
    state_district : str
        Composite field (e.g., "NY12").

    """

    state_district: str


class CommitteeItem(BaseModel):
    """Minimal representation of a committee roster entry.

    Used when parsing lower-level committee records or leadership
    references inside the Clerk data.

    Attributes
    ----------
    comcode : str
        Unique committee code (e.g., "HSAG").
    rank : str
        Rank or seniority within the committee.
    leadership : str, optional
        Leadership title (e.g., "Chair", "Ranking Member"), if applicable.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    comcode: str
    rank: str
    leadership: str | None = None


class CommitteeAssignment(BaseModel):
    """Assignment of a Member to a full committee.

    Attributes
    ----------
    comcode : str, optional
        Unique code for the committee.
    rank_str : str
        Text version of rank (e.g., "1").
    leadership : str, optional
        Title (e.g., "Chair").

    Computed Properties
    -------------------
    parsed_rank : int
    chamber_id : str
    parsed_leadership : str or None

    """

    model_config = ConfigDict(
        extra="allow",
    )
    comcode: str | None = None
    rank_str: Annotated[str, Field(alias="rank")]
    leadership: str | None = None
    type: str = "committee"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_rank(self) -> int:
        """Return numeric rank derived from the string rank field.

        Converts the string `rank_str` (which may be empty or null) to an
        integer. Defaults to `0` if the string is empty or undefined.

        Returns
        -------
        int
            Parsed rank as an integer. Returns 0 if `rank_str` is empty or
            null.

        """
        if self.rank_str == "":
            return 0
        elif self.rank_str is None:
            return 0
        else:
            return int(self.rank_str)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chamber_id(self) -> str:
        """Return the full committee chamber ID.

        Typically corresponds to the `comcode` value. Used for lookups and
        matching against external data.

        Returns
        -------
        str
            Committee ID string (or empty string if `comcode` is missing).

        """
        return self.comcode or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_leadership(self) -> str | None:
        """Return the inferred leadership role of the Member.

        If `leadership` is already provided, it is returned as-is.
        If not, the method infers "Ranking Member" for rank 1.

        Returns
        -------
        str or None
            Explicit or inferred leadership role, or `None` if not applicable.

        """
        if self.leadership is not None:
            return self.leadership
        elif self.rank_str == "1":
            return "Ranking Member"
        else:
            return None


class SubcommitteeAssignment(BaseModel):
    """Assignment of a Member to a subcommittee.

    Attributes
    ----------
    subcomcode : str, optional
        Unique code for the subcommittee.
    rank_str : str
        Text version of rank (e.g., "1").
    leadership : str, optional
        Title (e.g., "Chair").

    Computed Properties
    -------------------
    parsed_rank : int
    chamber_id : str
    parsed_leadership : str or None

    """

    model_config = ConfigDict(
        extra="allow",
    )
    subcomcode: str
    rank_str: Annotated[str, Field(alias="rank")]
    leadership: str | None = None
    type: str = "subcommittee"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_rank(self) -> int:
        """Return numeric rank derived from the string rank field.

        Converts the string `rank_str` to an integer. If the value is missing
        or empty, returns 0.

        Returns
        -------
        int
            Parsed rank as an integer, or 0 if `rank_str` is empty or None.

        """
        if self.rank_str == "":
            return 0
        elif self.rank_str is None:
            return 0
        else:
            return int(self.rank_str)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chamber_id(self) -> str:
        """Return the subcommittee's unique chamber ID.

        Uses the `subcomcode` field as the authoritative identifier for
        subcommittees in downstream processes.

        Returns
        -------
        str
            Subcommittee code or empty string if not set.

        """
        return self.subcomcode or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_leadership(self) -> str | None:
        """Return the inferred leadership role of the Member.

        Returns the explicit `leadership` value if provided. If absent,
        infers "Ranking Member" for rank 1.

        Returns
        -------
        str or None
            Leadership role name (explicit or inferred), or `None`.

        """
        if self.leadership is not None:
            return self.leadership
        elif self.rank_str == "1":
            return "Ranking Member"
        else:
            return None


class CommitteeAssignments(BaseModel):
    """Model representing all committee and subcommittee assignments.

    Encapsulates a Member's participation in committees and their
    subcommittees, unifying both under a common interface.

    Attributes
    ----------
    committee : Sequence[CommitteeAssignment] or CommitteeAssignment
        Member's full-committee assignments.
    subcommittee : Sequence[SubcommitteeAssignment] or SubcommitteeAssignment
        Member's subcommittee assignments (optional).

    Computed Properties
    -------------------
    all_assignments : list[CommitteeAssignment | SubcommitteeAssignment]
        Flattened list containing all assignment objects, including both
        full committee and subcommittee memberships.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    committee: Sequence[CommitteeAssignment] | CommitteeAssignment
    subcommittee: (
        Sequence[SubcommitteeAssignment] | SubcommitteeAssignment | None
    ) = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_assignments(
        self,
    ) -> list[CommitteeAssignment | SubcommitteeAssignment]:
        """Return all committee and subcommittee assignments as a single list.

        Handles both singular and list formats for `committee` and
        `subcommittee` fields, returning a normalized flat list of all
        assignments.

        Returns
        -------
        list[CommitteeAssignment or SubcommitteeAssignment]
            Combined assignments for a Member.

        """
        data: list[CommitteeAssignment | SubcommitteeAssignment] = []
        if isinstance(self.committee, CommitteeAssignment):
            data.append(self.committee)
        elif isinstance(self.committee, Sequence):
            for c in self.committee:
                data.append(c)
        if isinstance(self.subcommittee, SubcommitteeAssignment):
            data.append(self.subcommittee)
        elif isinstance(self.subcommittee, Sequence):
            for s in self.subcommittee:
                data.append(s)
        return data


class PredVacateDate(ElectedDate):
    """Inherits from ElectedDate."""

    text: str


class PredecessorInfoBase(BaseModel):
    """Information about a replaced Member of Congress.

    Includes vacate reason, prior party, name, and parsed date.

    Attributes
    ----------
    bioguide_id : str
        Bioguide ID of the former Member.
    cause : str
        Reason for departure.
    ...
    chamber : str
        Always "House" in this model.

    Computed Properties
    -------------------
    vacate_date : datetime or None
    namelist : str

    """

    model_config = ConfigDict(
        extra="allow",
    )
    cause: str
    lastname: Annotated[str, Field(alias="pred-lastname")]
    firstname: Annotated[str, Field(alias="pred-firstname")]
    middlename: Annotated[str | None, Field(alias="pred-middlename")] = None
    official_name: Annotated[str, Field(alias="pred-official-name")]
    formal_name: Annotated[str, Field(alias="pred-formal-name")]
    title: Annotated[None, Field(alias="pred-title")]
    bioguide_id: Annotated[str, Field(alias="pred-memindex")]
    sort_name: Annotated[str, Field(alias="pred-sort-name")]
    party: Annotated[str, Field(alias="pred-party")]
    vacate_date_data: Annotated[
        PredVacateDate, Field(alias="pred-vacate-date")
    ]
    footnote_ref: Annotated[str, Field(alias="pred-footnote-ref")]
    footnote: Annotated[str | None, Field(alias="pred-footnote")] = None
    chamber: str = "House"
    active: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def vacate_date(self) -> datetime | None:
        """Return the parsed date on which the predecessor vacated office.

        Parses the compact `pred-vacate-date` string into a `datetime` object.

        Returns
        -------
        datetime or None
            Parsed vacate date, or None if the value is invalid.

        """
        return self.vacate_date_data.parsed_date

    @computed_field  # type: ignore[prop-decorator]
    @property
    def namelist(self) -> str:
        """Return formatted name as 'Last, First [Middle]'.

        Combines name fields into a printable identifier string.

        Returns
        -------
        str
            Formatted full name for display.

        """
        if self.middlename is not None:
            return f"{self.lastname}, {self.firstname} {self.middlename}"
        else:
            return f"{self.lastname}, {self.firstname}"


class PredecessorInfo(PredecessorInfoBase):
    """Extended predecessor info with location and district info.

    Attributes
    ----------
    state_district : str
    state_postal_code : str
    state_fullname : str
    district : str

    """

    state_district: str
    state_postal_code: str
    state_fullname: str
    district: str


class MemberItem(BaseModel):
    """One congressional district and associated Member assignment.

    Includes both structured member info and nested committee/predecessor
    relationships.

    Attributes
    ----------
    state_district : str
        Composite district code.
    member_info : MemberInfoBase
        Main contact and bio information.
    committee_assignments : CommitteeAssignments
        Committee/subcommittee roles.
    predecessor_info : PredecessorInfoBase, optional
        If a Member replaced someone mid-Congress.

    Computed Properties
    -------------------
    parsed_member_info : MemberInfo
    parsed_predecessor_info : PredecessorInfo or None
    bioguide_id : str
        Fallback-resilient unique identifier resolution.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    state_district: Annotated[str, Field(alias="statedistrict")]
    member_info: Annotated[MemberInfoBase, Field(alias="member-info")]
    committee_assignments: Annotated[
        CommitteeAssignments, Field(alias="committee-assignments")
    ]
    predecessor_info: Annotated[
        PredecessorInfoBase | None, Field(alias="predecessor-info")
    ] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_member_info(self) -> MemberInfo:
        """Return a validated `MemberInfo` object from raw embedded data.

        Merges base member info with the `state_district` value.

        Returns
        -------
        MemberInfo
            Parsed and validated model instance for the Member.

        """
        base_info = self.member_info.model_dump(by_alias=True)
        base_info["state_district"] = self.state_district
        return MemberInfo.model_validate(base_info)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed_predecessor_info(self) -> PredecessorInfo | None:
        """Return parsed `PredecessorInfo` for replaced Member, if available.

        Combines base predecessor info with district and state metadata from
        the current Member.

        Returns
        -------
        PredecessorInfo or None
            Structured predecessor data, or None if not present.

        """
        if self.predecessor_info is None:
            return None
        else:
            base_info = self.predecessor_info.model_dump(by_alias=True)
            base_info["state_district"] = self.state_district
            base_info["state_postal_code"] = self.member_info.state_postal_code
            base_info["state_fullname"] = self.member_info.state_fullname
            base_info["district"] = self.member_info.district
            return PredecessorInfo.model_validate(base_info)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bioguide_id(self) -> str:
        """Return the bioguide ID for the Member or their predecessor.

        Uses `parsed_member_info` if available. Falls back to
        `parsed_predecessor_info` only if necessary.

        Returns
        -------
        str
            Bioguide identifier for the Member or predecessor.

        Raises
        ------
        AssertionError
            If no valid bioguide ID can be determined.

        """
        if self.parsed_member_info.bioguide_id is not None:
            return self.parsed_member_info.bioguide_id

        elif self.parsed_predecessor_info is not None:
            # TODO: need to fix the logic here
            assert self.parsed_predecessor_info.bioguide_id is not None
            return self.parsed_predecessor_info.bioguide_id
        else:
            assert self.parsed_member_info.bioguide_id is not None
            return self.parsed_member_info.bioguide_id

    chamber: str = "House"


class Members(BaseModel):
    """Wrapper for the collection of all House member items.

    Each element in the `member` list represents a congressional
    district entry containing member data, committee assignments,
    and any predecessor info.

    Attributes
    ----------
    member : Sequence[MemberItem]
        List of structured `MemberItem` objects, one per
        district or seat.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    member: Sequence[MemberItem]


class Ratio(BaseModel):
    """Represents majority/minority composition for a committee.

    Attributes
    ----------
    majority : int
        Number of majority party members assigned.
    minority : int
        Number of minority party members assigned.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    majority: int
    minority: int


class Subcommittee(BaseModel):
    """Subcommittee metadata and its parent linkage info.

    Attributes
    ----------
    subcomcode : str
        Unique subcommittee code (e.g., "HSAG15").
    ...
    ratio : Ratio
        Party composition.

    Computed Properties
    -------------------
    majority : int
    minority : int
    chamber_id : str
    thomas_id_prefix : str

    """

    model_config = ConfigDict(
        extra="allow",
    )
    subcomcode: str
    room: Annotated[str, Field(alias="subcom-room")]
    zipcode: Annotated[str, Field(alias="subcom-zip")]
    zipcode_suffix: Annotated[str, Field(alias="subcom-zip-suffix")]
    building_code: Annotated[str, Field(alias="subcom-building-code")]
    phone: Annotated[str, Field(alias="subcom-phone")]
    fullname: Annotated[str, Field(alias="subcommittee-fullname")]
    ratio: Ratio
    chamber: str = "House"
    committee_type: str = "Subcommittee"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def majority(self) -> int:
        """Return the number of majority party members on the subcommittee.

        Returns
        -------
        int
            Majority count from the subcommittee's ratio block.

        """
        return self.ratio.majority

    @computed_field  # type: ignore[prop-decorator]
    @property
    def minority(self) -> int:
        """Return the number of minority party members on the subcommittee.

        Returns
        -------
        int
            Minority count from the ratio field.

        """
        return self.ratio.minority

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chamber_id_prefix(self) -> str:
        """Return the two-letter prefix from the subcommittee code.

        Returns
        -------
        str
            Chamber-level prefix (e.g., 'HS').

        """
        return self.subcomcode[:2]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id_number(self) -> str:
        """Return the numeric portion of the subcommittee code.

        Returns
        -------
        str
            Identifier for the subcommittee excluding prefix.

        """
        return self.subcomcode[2:]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def thomas_id_prefix(self) -> str:
        """Return THOMAS-style ID prefix for subcommittees.

        Always prepends 'HS' regardless of original prefix.

        Returns
        -------
        str
            Legacy-compatible prefix for THOMAS datasets.

        """
        return "HS" + self.chamber_id_prefix

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chamber_id(self) -> str:
        """Return complete chamber ID for subcommittee.

        Constructed by combining prefix and code number.

        Returns
        -------
        str
            Unique subcommittee ID string.

        """
        return self.chamber_id_prefix + self.id_number


class Committee(BaseModel):
    """Full committee metadata, including contact and membership ratios.

    Attributes
    ----------
    comcode : str
        Unique chamber-level committee ID.
    ...
    subcommittee : list[Subcommittee], optional
        Nested list of subcommittees.

    Computed Properties
    -------------------
    majority : int
    minority : int
    chamber_id : str
    thomas_id_prefix : str

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: str
    comcode: str
    room: Annotated[str, Field(alias="com-room")]
    header_text: Annotated[str | None, Field(alias="com-header-text")] = None
    zipcode: Annotated[str, Field(alias="com-zip")]
    zipcode_suffix: Annotated[str, Field(alias="com-zip-suffix")]
    building_code: Annotated[str, Field(alias="com-building-code")]
    phone: Annotated[str, Field(alias="com-phone")]
    fullname: Annotated[str, Field(alias="committee-fullname")]
    ratio: Ratio
    subcommittee: Sequence[Subcommittee] | None = None
    chamber: str = "House"
    committee_type: str = "Committee"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def majority(self) -> int:
        """Return the number of majority party members on the committee.

        Pulled directly from the nested `ratio` block.

        Returns
        -------
        int
            Count of majority members.

        """
        return self.ratio.majority

    @computed_field  # type: ignore[prop-decorator]
    @property
    def minority(self) -> int:
        """Return the number of minority party members on the committee.

        Pulled from the `ratio` attribute.

        Returns
        -------
        int
            Count of minority members.

        """
        return self.ratio.minority

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chamber_id_prefix(self) -> str:
        """Return the two-letter chamber prefix from the committee code.

        Example: For `comcode='HSAP'`, this returns `'HS'`.

        Returns
        -------
        str
            Prefix identifying the chamber (e.g., 'HS', 'SS').

        """
        return self.comcode[:2]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id_number(self) -> str:
        """Return the numeric part of the committee code.

        Extracted by slicing off the prefix. For example, 'HSAG' → 'AG'.

        Returns
        -------
        str
            Code representing the committee's numeric ID.

        """
        return self.comcode[2:]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def thomas_id_prefix(self) -> str:
        """Return the THOMAS-style prefix used in legacy datasets.

        Prepends 'HS' to the chamber prefix. For example, 'HSAG' → 'HSHS'.

        Returns
        -------
        str
            Static prefix for integration with legacy systems.

        """
        return "HS" + self.chamber_id_prefix

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chamber_id(self) -> str:
        """Return the full chamber ID formed from prefix and numeric code.

        Used in internal IDs and crosswalks. Example: 'HSAG'.

        Returns
        -------
        str
            Combined identifier for this committee.

        """
        return self.chamber_id_prefix + self.id_number


class Committees(BaseModel):
    """Container model for all full committees in the Clerk dataset.

    Holds a list of committees and provides a convenience property to
    flatten both committees and their subcommittees into a single list.

    Attributes
    ----------
    committee : Sequence[Committee]
        List of `Committee` objects representing all full committees
        reported in the dataset.

    Computed Properties
    -------------------
    committees_and_subs : list[Committee | Subcommittee]
        Flattened list containing both full committees and nested
        subcommittees. Useful for indexing or joining with
        member assignments.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    committee: Sequence[Committee]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def committees_and_subs(self) -> list[Committee | Subcommittee]:
        """Return a flattened list of all committees and subcommittees.

        Iterates over each `Committee` in the `committee` list and combines
        both the top-level committee and any nested `subcommittee` entries
        into a single list.

        Useful for search indexing, filtering, or name/code resolution.

        Returns
        -------
        list[Committee or Subcommittee]
            Combined list of committees and subcommittees.

        """
        data: list[Committee | Subcommittee] = []
        for c in self.committee:
            if c.subcommittee is not None:
                for s in c.subcommittee:
                    data.append(s)
            data.append(c)
        return data


class MemberData(BaseModel):
    """Schema for Clerk-provided member and committee datasets.

    Attributes
    ----------
    publish_date : str
        Timestamp string when the YAML file was generated.
    title_info : TitleInfo
        Metadata header (Congress number, Clerk name, etc.).
    members : Members
        Member roster by district.
    committees : Committees
        Committees and subcommittees metadata.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    publish_date: Annotated[str, Field(alias="publish-date")]
    title_info: Annotated[TitleInfo, Field(alias="title-info")]
    members: Members
    committees: Committees


class ClerkData(BaseModel):
    """Top-level schema for Clerk of the House member + committee data.

    Wraps the `MemberData` object, loaded from the YAML structure.

    Attributes
    ----------
    data : MemberData
        Member + committee + header metadata block.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    data: Annotated[MemberData, Field(alias="MemberData")]
