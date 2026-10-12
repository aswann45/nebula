"""Schemas for parsing responses from the Senate Clerk XML feed.

Defines base response classes for use with Senate member rosters and other
XML-based endpoints. Provides parsed XML access and structured Pydantic models.
"""

from typing import Any, cast

import xmltodict

from nebula.schemas import APIServiceResponse
from nebula.senate_clerk.member_model import ClerkData
from nebula.senate_clerk.parsers import SenateMemberParser


class SenateClerkResponse(APIServiceResponse):
    """Base class for responses from the Senate Clerk.

    Wraps the raw XML response in a parser using `xmltodict`, exposing the
    content as a dictionary under the `data` property.

    Attributes
    ----------
    data : dict
        Parsed XML response body as a dictionary.
    """

    @property
    def data(self) -> dict:
        """Return the XML response as a parsed dictionary.

        Uses `xmltodict` to convert the raw XML into a native Python dict.
        Caches the result on first access.

        Returns
        -------
        dict
            XML response content as a dictionary.

        Raises
        ------
        ValueError
            If no response text is available to parse.
        """
        if self._data is None:
            if self.text is None:
                raise ValueError("Missing text in SenateClerkResponse")
            self._data = xmltodict.parse(self.text)
        return cast(dict, self._data)

    @data.setter
    def data(self, value: dict) -> None:
        self._data = value


class ClerkSenatorInfoResponse(SenateClerkResponse):
    """Typed wrapper for Senate roster response.

    Parses XML into a validated `ClerkData` model using the
    `SenatorItem` and `SenatorsData` schemas.
    """

    @property
    def parsed_data(self) -> ClerkData:
        """Return fully validated data from the Clerk XML response.

        Converts the parsed XML into a typed `ClerkData` object on first
        access.

        Returns
        -------
        ClerkData
            Structured object representing the full Senate membership.
        """
        if self._parsed_data is None:
            self._parsed_data = SenateMemberParser().parse(
                (self.text or "").encode()
            )
        return cast(ClerkData, self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: Any) -> None:
        self._parsed_data = value
