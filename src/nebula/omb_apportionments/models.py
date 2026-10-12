"""Validated source records for OMB's published JSON documents."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OMBSourceModel(BaseModel):
    """Preserve unrecognized source fields while accepting Python names."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class OMBSchedule(OMBSourceModel):
    """One source schedule row with exact account identifiers."""

    budget_agency_title: str | None = Field(None, alias="BudgetAgencyTitle")
    budget_bureau_title: str | None = Field(None, alias="BudgetBureauTitle")
    account_title: str | None = Field(None, alias="AccountTitle")
    allocation_agency_code: str | None = Field(
        None, alias="AllocationAgencyCode"
    )
    cgac_agency: str | None = Field(None, alias="CgacAgency")
    begin_poa: str | None = Field(None, alias="BeginPoa")
    end_poa: str | None = Field(None, alias="EndPoa")
    availability_type_code: str | None = Field(
        None, alias="AvailabilityTypeCode"
    )
    cgac_account: str | None = Field(None, alias="CgacAcct")
    allocation_subaccount: str | None = Field(None, alias="AllocationSubacct")
    iteration: str | None = Field(None, alias="Iteration")
    tafs_iteration_id: int | str | None = Field(None, alias="TafsIterationId")
    line_number: str | None = Field(None, alias="LineNumber")
    line_split: str | None = Field(None, alias="LineSplit")
    line_description: str | None = Field(None, alias="LineDescription")
    approved_amount: int | None = Field(None, alias="ApprovedAmount")
    footnote_number: str | None = Field(None, alias="FootnoteNumber")

    @field_validator(
        "allocation_agency_code",
        "cgac_agency",
        "begin_poa",
        "end_poa",
        "availability_type_code",
        "cgac_account",
        "allocation_subaccount",
        "iteration",
        "line_number",
        "line_split",
        "footnote_number",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        """Normalize blank nullable fields without changing codes."""
        return None if value == "" else value

    @field_validator("approved_amount", mode="before")
    @classmethod
    def validate_whole_amount(cls, value: object) -> int | None:
        """Accept exact whole amounts without truncating fractions."""
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("ApprovedAmount must be a whole number")
        if isinstance(value, int):
            return value
        if isinstance(value, (str, Decimal)):
            try:
                amount = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError(
                    "ApprovedAmount must be a whole number"
                ) from exc
            if amount.is_finite() and amount == amount.to_integral_value():
                return int(amount)
        raise ValueError("ApprovedAmount must be a whole number")


class OMBFootnote(OMBSourceModel):
    """A numbered OMB footnote with its complete text."""

    footnote_number: str | None = Field(None, alias="FootnoteNumber")
    footnote_text: str | None = Field(None, alias="FootnoteText")


class OMBApportionment(OMBSourceModel):
    """An OMB JSON file with typed schedules and footnotes."""

    file_id: int = Field(alias="FileId")
    file_name: str = Field(alias="FileName", min_length=1)
    fiscal_year: int = Field(alias="FiscalYear")
    approval_timestamp: datetime | None = Field(
        None, alias="ApprovalTimestamp"
    )
    folder: str | None = Field(None, alias="Folder")
    approver_title: str | None = Field(None, alias="ApproverTitle")
    funds_provided_by: str | None = Field(None, alias="FundsProvidedBy")
    schedule_data: list[OMBSchedule] = Field(
        default_factory=list, alias="ScheduleData"
    )
    footnote_data: list[OMBFootnote] = Field(
        default_factory=list, alias="FootnoteData"
    )

    @field_validator("approval_timestamp", mode="before")
    @classmethod
    def parse_approval_timestamp(cls, value: object) -> object:
        """Accept OMB's timestamp format and reject malformed values."""
        if value is None or isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise ValueError("approval timestamp must be a string")
        return datetime.strptime(value, "%Y-%m-%d-%H.%M.%S.%f")


class OMBApportionmentReference(BaseModel):
    """A validated JSON link found on the OMB HTML index."""

    url: str
    file_name: str
