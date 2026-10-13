"""Validated Congress.gov legislation records and requests."""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BillType = Literal[
    "hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"
]
AmendmentType = Literal["hamdt", "samdt", "suamdt"]


class CongressSourceModel(BaseModel):
    """Preserve additional fields published by Congress.gov."""

    model_config = ConfigDict(extra="allow")


class CongressPagination(CongressSourceModel):
    """Published result count and continuation URL."""

    count: int = Field(ge=0)
    next: str | None = None


class CongressAction(CongressSourceModel):
    """One action on a bill or amendment."""

    action_date: date = Field(alias="actionDate")
    text: str
    type: str | None = None
    action_code: str | None = Field(default=None, alias="actionCode")
    action_time: time | None = Field(default=None, alias="actionTime")


class CongressAmendment(CongressSourceModel):
    """One amendment associated with a bill."""

    congress: int = Field(ge=1)
    type: Literal["HAMDT", "SAMDT", "SUAMDT"]
    number: str = Field(min_length=1)
    url: str
    description: str | None = None
    update_date: datetime | None = Field(default=None, alias="updateDate")


class CongressActionPage(BaseModel):
    """One page of bill or amendment actions."""

    actions: list[CongressAction]
    pagination: CongressPagination


class CongressAmendmentPage(BaseModel):
    """One page of amendments associated with a bill."""

    amendments: list[CongressAmendment]
    pagination: CongressPagination


class CongressBillRequest(BaseModel):
    """Validated bill identity and page bounds."""

    congress: int = Field(ge=1)
    bill_type: BillType
    bill_number: int = Field(gt=0)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=250, ge=1, le=250)

    @field_validator("bill_type", mode="before")
    @classmethod
    def lowercase_bill_type(cls, value: object) -> object:
        """Accept common uppercase bill type spelling."""
        return value.lower() if isinstance(value, str) else value


class CongressAmendmentRequest(BaseModel):
    """Validated amendment identity and page bounds."""

    congress: int = Field(ge=1)
    amendment_type: AmendmentType
    amendment_number: int = Field(gt=0)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=250, ge=1, le=250)

    @field_validator("amendment_type", mode="before")
    @classmethod
    def lowercase_amendment_type(cls, value: object) -> object:
        """Accept common uppercase amendment type spelling."""
        return value.lower() if isinstance(value, str) else value
