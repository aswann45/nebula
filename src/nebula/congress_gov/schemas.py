"""Response adapters for Congress.gov external API services.

Defines API response types for parsing and validating member-related
data from Congress.gov. Extends base `APIServiceResponse` for unified
error handling, logging, and lazy parsing.
"""

import json
from typing import Any, cast

from nebula.congress_gov.member_model import Member
from nebula.congress_gov.parsers import CongressGovMemberParser
from nebula.schemas import APIServiceResponse


class CongressGovResponse(APIServiceResponse):
    """Generic Congress.gov API response.

    Provides raw response access and ensures response JSON is present
    before casting to dict.

    Attributes
    ----------
    data : dict
        Raw response JSON content parsed from HTTP response.

    Raises
    ------
    ValueError
        If no response JSON is present in the API response.

    """

    @property
    def data(self) -> dict:
        """Return parsed JSON response as a dictionary.

        Lazily loads and caches the response body.

        Returns
        -------
        dict
            Response payload parsed from JSON.

        Raises
        ------
        ValueError
            If `response_json` is missing.

        """
        if self._data is None:
            if self.response_json is None:
                raise ValueError("Missing text in CongressGovResponse")
            self._data = self.response_json
        return cast(dict, self._data)

    @data.setter
    def data(self, value: dict) -> None:
        """Set the raw parsed data dictionary.

        Parameters
        ----------
        value : dict
            Dictionary representing raw response content.

        """
        self._data = value


class CongressGovMemberResponse(CongressGovResponse):
    """Typed response handler for Member records from Congress.gov API.

    Hydrates the `parsed_data` field as a fully validated `Member` model
    from the JSON payload.
    """

    @property
    def parsed_data(self) -> Member:
        """Return parsed and validated Member object.

        Uses `MemberResponseModel` to extract the `member` payload and
        cast it to a Pydantic model.

        Returns
        -------
        Member
            Fully structured Member instance from Congress.gov.

        Raises
        ------
        ValidationError
            If response JSON cannot be validated.

        """
        if self._parsed_data is None:
            content = (
                json.dumps(self.response_json).encode()
                if self.response_json is not None
                else (self.text or "").encode()
            )
            self._parsed_data = CongressGovMemberParser().parse(content)
        return cast(Member, self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: Any) -> None:
        """Set the parsed Member model manually.

        Parameters
        ----------
        value : Any
            Must be a `Member` instance or compatible object.

        """
        self._parsed_data = value
