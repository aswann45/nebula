"""Schemas and response classes for GitHub-based Congressional data.

Parses YAML-based member metadata from the `unitedstates/congress-legislators`
GitHub repository, including historical records, terms, and leadership roles.
"""

from datetime import datetime
from typing import Any, Literal, cast

import inflect
import us
import yaml
from pydantic import BaseModel, Field

from nebula.github_congress.models import GitHubCommittee
from nebula.schemas import APIServiceResponse
from nebula.typings import MemberInfoDict


class HistoricalMemberIDData(BaseModel):
    """Schema for member identifiers in historical YAML records.

    Attributes
    ----------
    bioguide : str
        Bioguide ID (primary unique identifier).
    """

    bioguide: str = Field(...)


class HistoricalMemberNameData(BaseModel):
    """Name components for a historical member entry.

    Attributes
    ----------
    first : str
        First name.
    last : str
        Last name.
    middle : str, optional
        Middle name.
    official_full : str, optional
        Official full name.
    suffix : str, optional
        Name suffix (e.g., Jr., III).
    """

    first: str = Field(...)
    last: str = Field(...)
    middle: str | None = Field(default=None)
    official_full: str | None = Field(default=None)
    suffix: str | None = Field(default=None)


class HistoricalMemberTermData(BaseModel):
    """Single term served by a historical member.

    Attributes
    ----------
    type_ : str
        Chamber type ("rep" or "sen").
    start : str
        Start date (YYYY-MM-DD).
    end : str
        End date (YYYY-MM-DD).
    state : str
        Two-letter postal abbreviation.
    district : int, optional
        District number (House only).
    party : str, optional
        Political party.
    phone : str, optional
        Office phone number.
    address : str, optional
        Office mailing address.
    office : str, optional
        Office room/building.
    url : str, optional
        Member's website.
    """

    type_: str = Field(..., alias="type")
    start: str = Field(...)
    end: str = Field(...)
    state: str = Field(...)
    district: int | None = Field(default=None)
    party: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    address: str | None = Field(default=None)
    office: str | None = Field(default=None)
    url: str | None = Field(default=None)


class HistoricalMemberData(BaseModel):
    """Top-level model for a historical congressional member.

    Attributes
    ----------
    id_ : HistoricalMemberIDData
        Nested object with identifier fields.
    name : HistoricalMemberNameData
        Nested object with name components.
    terms : list[HistoricalMemberTermData]
        List of terms served.
    active : bool
        Whether the member is currently serving.
    """

    id_: HistoricalMemberIDData = Field(..., alias="id")
    name: HistoricalMemberNameData = Field(...)
    terms: list[HistoricalMemberTermData] = Field(min_length=1)
    active: bool = Field(default=False)

    @property
    def bioguide_id(self) -> str:
        """Return the member's Bioguide ID."""
        return self.id_.bioguide

    @property
    def lastname(self) -> str:
        """Return the Member's last name."""
        return self.name.last

    @property
    def firstname(self) -> str:
        """Return the Member's first name."""
        return self.name.first

    @property
    def middlename(self) -> str | None:
        """Return the Member's middle name or None."""
        return self.name.middle

    @property
    def suffix(self) -> str | None:
        """Return the Member's name's suffix or None."""
        return self.name.suffix

    @property
    def namelist(self) -> str:
        """Return the Member's comma-separated last and first names."""
        return f"{self.lastname}, {self.firstname}"

    @property
    def sort_name(self) -> str:
        """Return the namelist attribute in uppercase."""
        return self.namelist.upper().replace(" ", "")

    @property
    def official_name(self) -> str | None:
        """Return the full official name or fallback based on components."""
        if self.name.official_full is None:
            if self.suffix is not None:
                return f"{self.firstname} {self.lastname}, {self.suffix}"
            else:
                return f"{self.firstname} {self.lastname}"
        return self.name.official_full

    @property
    def formal_name(self) -> str | None:
        """Return the Member's official name."""
        return self.official_name

    @property
    def party(self) -> Literal["D", "R", "I"]:
        """Return party abbreviation ('D', 'R', 'I') from most recent term."""
        if self.terms[-1].party == "Democrat":
            return "D"
        elif self.terms[-1].party == "Republican":
            return "R"
        else:
            return "I"

    @property
    def chamber(self) -> Literal["House", "Senate"]:
        """Return the Member's chamber from the most recent term."""
        if self.terms[-1].type_ == "rep":
            return "House"
        else:
            return "Senate"

    @property
    def state_postal_code(self) -> str:
        """Return the postal abbreviation for the Member's state."""
        return self.terms[-1].state

    @property
    def state_fullname(self) -> str:
        """Return the name of the Member's state."""
        try:
            return us.states.lookup(state := self.terms[-1].state).name  # type: ignore[union-attr]
        except AttributeError as ae:
            raise ValueError(
                f"Could not resolve state name from {state}"
            ) from ae

    @property
    def district(self) -> str | None:
        """Return the number for the Member's district or None."""
        if self.terms[-1].type_ == "rep":
            p = inflect.engine()
            return p.ordinal(str(self.terms[-1].district))
        else:
            return None

    @property
    def state_district(self) -> str | None:
        """Return the abbreviation for the Member's distict."""
        if self.terms[-1].type_ == "rep":
            return self.terms[-1].state + str(self.terms[-1].district).zfill(2)
        else:
            return None

    @property
    def elected_date(self) -> datetime:
        """Return the datetime for the date of the Member's first election."""
        return datetime.strptime(self.terms[0].start, "%Y-%m-%d")

    @property
    def sworn_date(self) -> datetime:
        """Return the Member's date of election."""
        return self.elected_date

    @property
    def vacate_date(self) -> datetime:
        """Return the end date of the last term as a datetime."""
        return datetime.strptime(self.terms[-1].end, "%Y-%m-%d")


class GitHubCongressResponse(APIServiceResponse):
    """Response class for YAML-based GitHub Congress data.

    Parses YAML from the `text` field into a dictionary.

    Attributes
    ----------
    data : dict
        Parsed YAML content as a dictionary.

    Raises
    ------
    ValueError
        If `text` is missing.
    """

    @property
    def data(self) -> dict:
        """Return parsed YAML response data from the GitHub Congress dataset.

        Converts the raw YAML text payload into a Python dictionary using
        `yaml.safe_load`. Lazily loads and caches the parsed data for
        repeated access.

        Returns
        -------
        dict
            Parsed YAML content representing the GitHub Congress dataset.

        Raises
        ------
        ValueError
            If `text` is missing from the response and parsing cannot proceed.
        """
        if self._data is None:
            if self.text is None:
                raise ValueError("Missing text in GitHubCongressResponse")
            self._data: dict[str, Any] = yaml.safe_load(self.text)
        return self._data

    @data.setter
    def data(self, value: dict) -> None:
        """Set the parsed YAML data manually.

        Parameters
        ----------
        value : dict
            Pre-parsed YAML data to assign to the response.
        """
        self._data = value


class GHCCurrentMemberResponse(GitHubCongressResponse):
    """Parser for currently serving Members from GitHub YAML.

    Transforms raw YAML records into flattened `MemberInfoDict` structures,
    applying leadership and term logic.

    Attributes
    ----------
    parsed_data : list[MemberInfoDict]
        Processed member data.
    """

    @property
    def parsed_data(self) -> list[MemberInfoDict]:
        """Return parsed current member data from GitHub YAML.

        Parses the raw YAML response using `parse_member_data` and returns
        a list of member metadata dictionaries, including leadership roles
        and term information.

        Returns
        -------
        list[MemberInfoDict]
            Structured data for currently serving Members.
        """
        if self._parsed_data is None:
            self._parsed_data = self.parse_member_data()
        return cast(list[MemberInfoDict], self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: list[MemberInfoDict]) -> None:
        """Set the parsed member data manually.

        Parameters
        ----------
        value : list[MemberInfoDict]
            Pre-parsed list of member dictionaries.
        """
        self._parsed_data = value

    def parse_single_member(self, member_dict: dict) -> MemberInfoDict | None:
        """Extract relevant fields from a single YAML member record.

        Parameters
        ----------
        member_dict : dict
            Raw YAML dictionary representing a Member.

        Returns
        -------
        MemberInfoDict or None
            Structured member info or None if no valid data found.
        """
        res = {}
        if (
            leadership_roles := member_dict.get("leadership_roles")
        ) is not None:
            current_roles = [
                r
                for r in leadership_roles
                if r.get("end") is None
                or datetime.strptime(r.get("end"), "%Y-%m-%d")
                >= datetime.now()
            ]

            reshaped_roles = []
            for role in current_roles:
                reshaped_roles.append(
                    {
                        "role_name": role.get("title"),
                        "level": "leadership",
                    }
                )

            res.update(
                {
                    "leadership_roles": reshaped_roles,
                    "bioguide_id": member_dict.get("id", {}).get("bioguide"),
                }
            )

        if (terms := member_dict.get("terms")) is not None:
            res.update(
                {
                    "terms": terms,
                    "bioguide_id": member_dict.get("id", {}).get("bioguide"),
                }
            )

        if len(res) == 0:
            return None

        return res

    def parse_member_data(self) -> list[MemberInfoDict]:
        """Transform the full YAML dataset into structured member records.

        Returns
        -------
        list[MemberInfoDict]
            Parsed current member entries.
        """
        return [
            member
            for _m in self.data
            if (member := self.parse_single_member(_m)) is not None
        ]


class GHCCurrentCommitteeResponse(GitHubCongressResponse):
    """Typed committee data from the published GitHub YAML.

    Attributes
    ----------
    parsed_data : list[GitHubCommittee]
        Validated committee records.
    """

    @property
    def parsed_data(self) -> list[GitHubCommittee]:
        """Return validated committee records from the YAML body."""
        if self._parsed_data is None:
            from .parsers import GitHubCommitteeParser

            self._parsed_data = GitHubCommitteeParser().parse(
                (self.text or "").encode()
            )
        return cast(list[GitHubCommittee], self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: Any) -> None:
        self._parsed_data = value


class GHCHistoricalMemberResponse(GitHubCongressResponse):
    """Parser for historical member records by year.

    Attributes
    ----------
    year : str or int
        Filter year for returned members.
    parsed_data : list[HistoricalMemberData]
        List of member records with service extending through `year`.
    """

    year: str | int = Field(...)

    @property
    def parsed_data(self) -> list[HistoricalMemberData]:
        """Return filtered historical member data based on service year.

        Validates and transforms raw YAML into `HistoricalMemberData` models,
        then filters to include only Members whose last service year is greater
        than or equal to the given year.

        Returns
        -------
        list[HistoricalMemberData]
            List of historical Members active during or after the filter year.
        """
        if self._parsed_data is None:
            self._parsed_data = self.parse_member_data(self.year)
        return cast(list[HistoricalMemberData], self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: list[MemberInfoDict]) -> None:
        """Set parsed historical member data manually.

        Parameters
        ----------
        value : list[MemberInfoDict]
            Pre-parsed list of member records (must match expected shape).
        """
        self._parsed_data = value

    def parse_member_data(self, year: str | int) -> list[HistoricalMemberData]:
        """Filter members who were active in or after the specified year.

        Parameters
        ----------
        year : str or int
            Year to use as lower bound for inclusion.

        Returns
        -------
        list[HistoricalMemberData]
            Member records matching the year threshold.
        """
        data = [HistoricalMemberData.model_validate(m) for m in self.data]
        return [
            d
            for d in data
            if d.vacate_date.year >= datetime.strptime(str(year), "%Y").year
        ]
