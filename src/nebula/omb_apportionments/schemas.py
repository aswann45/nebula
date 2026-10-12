"""Response schemas for parsing OMB apportionments data.

Includes HTML page scraping for index listings and structured JSON parsing
for individual apportionment files published by OMB. Handles date coercion,
field normalization, and nested data structures.
"""

import json
import re
from datetime import datetime
from typing import Any, cast

from bs4 import BeautifulSoup, Tag
from pydantic import ConfigDict

from nebula.schemas import APIServiceResponse


class OMBApportionmentsPageResponse(APIServiceResponse):
    """Response handler for the main OMB apportionments HTML listing page.

    Uses BeautifulSoup to parse the HTML and extract all downloadable
    JSON file links. These files represent individual apportionments.
    """

    @property
    def data(self) -> BeautifulSoup:
        """Parse the response HTML into a BeautifulSoup document tree.

        Returns
        -------
        BeautifulSoup
            Parsed representation of the response HTML.

        Raises
        ------
        ValueError
            If the HTML response body is missing.
        """
        if self._data is None:
            if self.text is None:
                raise ValueError(
                    "Missing text in OMBApportionmentsPageResponse"
                )
            self._data = BeautifulSoup(
                self.text, "html.parser", multi_valued_attributes=False
            )
        return cast(BeautifulSoup, self._data)

    @data.setter
    def data(self, value: dict) -> None:
        self._data = value

    @property
    def parsed_data(self) -> list[Tag]:
        """Extract JSON file link tags from the HTML document.

        Matches all anchor (`<a>`) tags whose `href` ends in `.json`.

        Returns
        -------
        list[Tag]
            List of anchor tags pointing to apportionment JSON files.
        """
        if self._parsed_data is None:
            self._parsed_data = self.data.find_all(href=re.compile(r".json$"))
        return cast(list[Tag], self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: Any) -> None:
        self._parsed_data = value

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )


class OMBSingleApportionmentResponse(APIServiceResponse):
    """Response handler for an individual OMB apportionment JSON file.

    Parses the structured JSON into key fields, including nested
    schedule and footnote blocks. Normalizes field names to `snake_case`
    and handles type coercion for dates and numerics.

    Attributes
    ----------
    snake_case_pattern : re.Pattern
        Regex used to convert CamelCase fields to snake_case.
    """

    snake_case_pattern: re.Pattern = re.compile(r"(?<!^)(?=[A-Z])")

    @property
    def data(self) -> dict:
        """Return parsed JSON response body as a dictionary.

        Returns
        -------
        dict
            Dictionary parsed from the JSON response.

        Raises
        ------
        ValueError
            If the response body is missing or invalid.
        """
        if self._data is None:
            if self.text is None:
                raise ValueError(
                    "Missing text in OMBSingleApportionmentsResponse"
                )
            self._data: dict[str, Any] = json.loads(self.text)
        return self._data

    @data.setter
    def data(self, value: dict) -> None:
        self._data = value

    @property
    def parsed_data(self) -> dict:
        """Return normalized and transformed apportionment data.

        Includes parsed schedule and footnote blocks, as well as
        coerced date and integer fields.

        Returns
        -------
        dict
            Fully structured apportionment dataset.
        """
        if self._parsed_data is None:
            self._parsed_data = self.parse_apportionment_info(self.data)
        return cast(dict, self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: Any) -> None:
        self._parsed_data = value

    def _coerce_datetime(self, date: str) -> datetime | None:
        """Convert a string to a datetime, or return None if invalid.

        Expected format is `YYYY-MM-DD-HH.MM.SS.micro`.

        Parameters
        ----------
        date : str
            Timestamp string to convert.

        Returns
        -------
        datetime or None
            Parsed `datetime` object or None if parsing fails.
        """
        try:
            return datetime.strptime(date, "%Y-%m-%d-%H.%M.%S.%f")
        except ValueError:
            return None

    def parse_apportionment_info(self, apportionment_dict: dict) -> dict:
        """Normalize high-level fields from an OMB apportionment JSON file.

        Extracts scalar metadata and nested `ScheduleData` and `FootnoteData`.

        Parameters
        ----------
        apportionment_dict : dict
            Raw JSON dictionary parsed from a file.

        Returns
        -------
        dict
            Normalized and enriched representation of the apportionment.
        """
        data = {
            "file_id": apportionment_dict["FileId"],
            "file_name": apportionment_dict["FileName"],
            "fiscal_year": int(apportionment_dict["FiscalYear"]),
            "approval_timestamp": self._coerce_datetime(
                apportionment_dict["ApprovalTimestamp"]
            ),
            "folder": apportionment_dict["Folder"],
            "approver_title": apportionment_dict["ApproverTitle"],
            "funds_provided_by": apportionment_dict["FundsProvidedBy"],
        }
        data["schedue_data"] = [
            self.parse_schedule_data(schedule)
            for schedule in apportionment_dict["ScheduleData"]
        ]
        data["footnote_data"] = [
            self.parse_footnote_data(footnote)
            for footnote in apportionment_dict["FootnoteData"]
        ]
        return data

    def parse_schedule_data(self, schedule_dict: dict) -> dict:
        """Transform a single `ScheduleData` block into normalized form.

        Converts field names to snake_case, coerces types, and renames select
        fields for downstream use.

        Parameters
        ----------
        schedule_dict : dict
            One schedule entry from the JSON block.

        Returns
        -------
        dict
            Normalized schedule row.
        """
        data = {}
        fields = [
            "BudgetAgencyTitle",
            "BudgetBureauTitle",
            "AccountTitle",
            "AllocationAgencyCode",
            "CgacAgency",
            "BeginPoa",
            "EndPoa",
            "AvailabilityTypeCode",
            "CgacAcct",
            "AllocationSubacct",
            "Iteration",
            "TafsIterationId",
            "LineNumber",
            "LineSplit",
            "LineDescription",
            "ApprovedAmount",
            "FootnoteNumber",
        ]

        empty_str_fields = [
            "allocation_agency_code",
            "begin_poa",
            "end_poa",
            "availability_type_code",
            "allocation_subacct",
            "line_split",
            "footnote_number",
        ]

        int_fields = [
            "iteration",
            "begin_poa",
            "end_poa",
        ]

        rename_fields = {
            "cgac_acct": "cgac_account",
            "allocation_subacct": "allocation_subaccount",
        }

        for field in fields:
            data[self.snake_case_pattern.sub("_", field).lower()] = (
                schedule_dict.get(field)
            )
        for field in empty_str_fields:
            if data[field] == "":
                data[field] = None
        for field in int_fields:
            if isinstance(data[field], str):
                data[field] = int(data[field])  # type: ignore
        for field, new_field in rename_fields.items():
            data[new_field] = data.pop(field)

        return data

    def parse_footnote_data(self, footnote_dict: dict) -> dict:
        """Normalize a single `FootnoteData` block.

        Parameters
        ----------
        footnote_dict : dict
            Dictionary representing one footnote record.

        Returns
        -------
        dict
            Dictionary with `footnote_number` and `footnote_text`.
        """
        data = {
            "footnote_number": footnote_dict.get("FootnoteNumber"),
            "footnote_text": footnote_dict.get("FootnoteText"),
        }
        return data
