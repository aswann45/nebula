"""Pydantic models for parsing Congress.gov Member API responses.

Includes data representations for Members of Congress, their terms,
party history, leadership roles, sponsored/cosponsored legislation,
depictions, and office contact information.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class AddressInformation(BaseModel):
    """Contact and location information for a Member.

    Attributes
    ----------
    city : str, optional
        Office city.
    district : str, optional
        Congressional district (if applicable).
    office_address : str, optional
        Full office mailing address.
    phone_number : str, optional
        Office phone number.
    zip_code : int, optional
        Postal zip code.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    city: str | None = None
    district: str | None = None
    office_address: Annotated[
        str | None, Field(alias="officeAddress", default=None)
    ]
    phone_number: Annotated[
        str | None, Field(alias="phoneNumber", default=None)
    ]
    zip_code: Annotated[int | None, Field(alias="zipCode", default=None)]


class CosponsoredLegislation(BaseModel):
    """Metadata about cosponsored bills.

    Attributes
    ----------
    count : int
        Total number of bills cosponsored by the Member.
    url : str
        Link to full cosponsorship list on Congress.gov.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    count: int
    url: str


class Depiction(BaseModel):
    """Portrait or image metadata for the Member.

    Attributes
    ----------
    attribution : str, optional
        Source or copyright info for the image.
    image_url : str
        Direct URL to the image.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    attribution: str | None = None
    image_url: Annotated[str, Field(alias="imageUrl")]


class LeadershipItem(BaseModel):
    """Represents a leadership role held by a Member.

    Attributes
    ----------
    congress : int
        Congress in which the role was held.
    role_name : str
        Role title or type (e.g., "Chair", "Ranking Member").
    current : bool, optional
        Whether the Member currently holds this role.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    congress: int
    role_name: Annotated[str, Field(alias="type")]
    current: bool | None = None


class PartyHistoryItem(BaseModel):
    """Party affiliation history for a Member.

    Attributes
    ----------
    party_abbreviation : str
        Shortened party name (e.g., "D", "R").
    party_name : str
        Full name of the party (e.g., "Democrat").
    start_year : int
        Year this party affiliation began.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    party_abbreviation: Annotated[str, Field(alias="partyAbbreviation")]
    party_name: Annotated[str, Field(alias="partyName")]
    start_year: Annotated[int, Field(alias="startYear")]


class SponsoredLegislation(CosponsoredLegislation):
    """Metadata about sponsored legislation.

    Inherits structure from `CosponsoredLegislation`.
    """

    pass


class Term(BaseModel):
    """A single congressional term served by a Member.

    Attributes
    ----------
    chamber : str
        Legislative chamber (e.g., "House", "Senate").
    congress : int
        Congress number (e.g., 118).
    district : int, optional
        House district number (if applicable).
    end_year : int, optional
        Year the term ended.
    member_type : str
        Role type (e.g., "Representative", "Senator").
    start_year : int
        Year the term began.
    state_code : str
        Two-letter postal abbreviation (e.g., "NY").
    state_name : str
        Full name of the state (e.g., "New York").
    """

    model_config = ConfigDict(
        extra="allow",
    )
    chamber: str
    congress: int
    district: int | None = None
    end_year: Annotated[int | None, Field(alias="endYear")] = None
    member_type: Annotated[str, Field(alias="memberType")]
    start_year: Annotated[int, Field(alias="startYear")]
    state_code: Annotated[str, Field(alias="stateCode")]
    state_name: Annotated[str, Field(alias="stateName")]


class Member(BaseModel):
    """Full data model for a Member of Congress.

    Attributes
    ----------
    bioguide_id : str
        Unique Bioguide ID.
    birth_year : str, optional
        Four-digit birth year (as string).
    cosponsored_legislation : CosponsoredLegislation, optional
        Metadata about cosponsored bills.
    current_member : bool
        Whether the individual is a current Member.
    depiction : Depiction, optional
        Official image and attribution.
    direct_order_name : str
        Name in direct order (e.g., "Jane Doe").
    district : int, optional
        House district number, if applicable.
    first_name : str
        First name of the Member.
    inverted_order_name : str
        Name in last-first format (e.g., "Doe, Jane").
    last_name : str
        Last name of the Member.
    party_history : list[PartyHistoryItem]
        Historical list of party affiliations.
    sponsored_legislation : SponsoredLegislation, optional
        Metadata on sponsored bills.
    state : str
        Two-letter state abbreviation.
    terms : list[Term]
        All terms served by the Member.
    update_date : str
        Last update timestamp from Congress.gov.
    leadership : list[LeadershipItem], optional
        List of leadership roles.
    honorific_name : str, optional
        Title or prefix (e.g., "Senator", "Congresswoman").
    official_website_url : str, optional
        Link to the Member's official website.
    address_information : AddressInformation, optional
        Office location and contact info.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    bioguide_id: Annotated[str, Field(alias="bioguideId")]
    birth_year: Annotated[str | None, Field(alias="birthYear")] = None
    cosponsored_legislation: Annotated[
        CosponsoredLegislation | None,
        Field(alias="cosponsoredLegislation", default=None),
    ]
    current_member: Annotated[bool, Field(alias="currentMember")]
    depiction: Depiction | None = None
    direct_order_name: Annotated[str, Field(alias="directOrderName")]
    district: int | None = None
    first_name: Annotated[str, Field(alias="firstName")]
    inverted_order_name: Annotated[str, Field(alias="invertedOrderName")]
    last_name: Annotated[str, Field(alias="lastName")]
    party_history: Annotated[
        Sequence[PartyHistoryItem], Field(alias="partyHistory")
    ]
    sponsored_legislation: Annotated[
        SponsoredLegislation | None,
        Field(alias="sponsoredLegislation", default=None),
    ]
    state: str
    terms: Sequence[Term] = Field(min_length=1)
    update_date: Annotated[str, Field(alias="updateDate")]
    leadership: Sequence[LeadershipItem] | None = None
    honorific_name: Annotated[str | None, Field(alias="honorificName")] = None
    official_website_url: Annotated[
        str | None, Field(alias="officialWebsiteUrl")
    ] = None
    address_information: Annotated[
        AddressInformation | None, Field(alias="addressInformation")
    ] = None


class Request(BaseModel):
    """Echoes request metadata from the Congress.gov API.

    Attributes
    ----------
    bioguide_id : str
        The Bioguide ID requested.
    content_type : str
        Response content type requested (e.g., "json").
    format : str
        Format string requested in the API call (e.g., "json").
    """

    model_config = ConfigDict(
        extra="allow",
    )
    bioguide_id: Annotated[str, Field(alias="bioguideId")]
    content_type: Annotated[str, Field(alias="contentType")]
    format: str


class MemberResponseModel(BaseModel):
    """Top-level response from the Congress.gov Member API.

    Attributes
    ----------
    member : Member
        Parsed member data.
    request : Request
        Metadata about the original API call.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    member: Member
    request: Request
