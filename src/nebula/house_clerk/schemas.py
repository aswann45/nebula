"""Schemas for handling XML-based responses from the Clerk of the House.

Parses responses for both roll call votes and member rosters into
structured formats using Pydantic and XML parsing (via xmltodict).
"""

from datetime import datetime
from typing import Any, cast

import xmltodict
from pydantic import Field

from nebula.house_clerk.member_model import ClerkData
from nebula.house_clerk.parsers import HouseMemberParser
from nebula.schemas import APIServiceResponse
from nebula.typings import (
    RecordedVote,
    RollCallDict,
    VoteMeta,
)


class HouseClerkResponse(APIServiceResponse):
    """Base class for responses from the Clerk of the House.

    Parses XML content into dictionaries using `xmltodict` and provides
    cached access to the parsed data.

    Attributes
    ----------
    data : dict
        XML response content parsed into a dictionary.
    """

    @property
    def data(self) -> dict:
        """Return parsed XML content as a Python dictionary.

        Parses and caches the response XML using `xmltodict`.

        Returns
        -------
        dict
            Parsed XML data.

        Raises
        ------
        ValueError
            If no response text is available.
        """
        if self._data is None:
            if self.text is None:
                raise ValueError("Missing text in HouseClerkResponse")
            self._data = xmltodict.parse(
                self.text, attr_prefix="", cdata_key="text"
            )
        return cast(dict, self._data)

    @data.setter
    def data(self, value: dict) -> None:
        self._data = value


class ClerkMemberInfoResponse(HouseClerkResponse):
    """Typed response wrapper for Clerk member roster data.

    Parses the member roster XML using the `ClerkData` model.
    """

    @property
    def parsed_data(self) -> ClerkData:
        """Return structured Clerk member data parsed from XML.

        Returns
        -------
        ClerkData
            Validated model of the Clerk-provided member dataset.
        """
        if self._parsed_data is None:
            self._parsed_data = HouseMemberParser().parse(
                (self.text or "").encode()
            )
        return cast(ClerkData, self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: Any) -> None:
        self._parsed_data = value


class ClerkRollCallResponse(HouseClerkResponse):
    """Typed response wrapper for Clerk roll call vote data.

    Parses metadata and recorded votes from XML, including vote question,
    result, action date, and individual member votes.

    Attributes
    ----------
    year : int
        Legislative year associated with the roll call vote.
    """

    year: int = Field(..., description="Legislative year")

    @property
    def parsed_data(self) -> RollCallDict:
        """Return full roll call vote metadata and votes.

        Extracts metadata from the vote header and individual recorded
        member votes. Includes the associated `year`.

        Returns
        -------
        RollCallDict
            Dictionary with `vote_meta`, `year`, and `votes` keys.
        """
        if self._parsed_data is None:
            self._parsed_data = {}
            self._parsed_data = self.parse_vote_meta()
            self._parsed_data["year"] = self.year
            self._parsed_data["votes"] = [
                self.parse_member_vote(v)
                for v in self.data["rollcall-vote"]["vote-data"][
                    "recorded-vote"
                ]
            ]
        return cast(RollCallDict, self._parsed_data)

    @parsed_data.setter
    def parsed_data(self, value: Any) -> None:
        self._parsed_data = value

    def _coerce_datetime(self, dt: str) -> datetime:
        """Coerce datetime string to datetime object. Format is d-MMM-YYYY."""
        return datetime.strptime(dt, "%d-%b-%Y")

    def parse_vote_meta(self) -> VoteMeta:
        """Extract and format metadata from a Clerk roll call vote.

        Parses fields such as congress number, session, question, description,
        result, and amendment references.

        Returns
        -------
        VoteMeta
            Structured dictionary containing vote metadata.

        Raises
        ------
        KeyError
            If required keys are missing from the XML payload.
        """
        try:
            _vote_meta = self.data["rollcall-vote"]["vote-metadata"]
            return {
                "congress": int(_vote_meta["congress"]),
                "session": _vote_meta["session"],
                "chamber": "House",
                "roll_call_number": int(_vote_meta["rollcall-num"]),
                "bill_number": _vote_meta.get("legis-num"),
                "vote_question": _vote_meta["vote-question"],
                "vote_description": str(_vote_meta["vote-desc"]),
                "vote_type": _vote_meta["vote-type"],
                "vote_result": _vote_meta["vote-result"],
                "action_date": self._coerce_datetime(
                    _vote_meta["action-date"]
                ),
                "majority": _vote_meta["majority"],
                "amendment_author": _vote_meta.get("amendment-author"),
                "amendment_number_offered": int(num)
                if (num := _vote_meta.get("amendment-num")) is not None
                else None,
            }
        except KeyError as e:
            raise KeyError(f"Missing key {e} in {self.data}") from e

    def parse_member_vote(self, vote_dict: dict) -> RecordedVote:
        """Parse a single recorded vote from the Clerk data.

        Parameters
        ----------
        vote_dict : dict
            Dictionary representing a single legislator's vote.

        Returns
        -------
        RecordedVote
            Parsed and normalized member vote.

        Raises
        ------
        KeyError
            If expected keys are missing from the vote dictionary.
        """
        try:
            _vote = vote_dict["legislator"]
            return {
                "bioguide_id": _vote["name-id"],
                "vote": vote_dict["vote"],
                "party": _vote["party"],
                "member_last_name": _vote["text"],
            }
        except KeyError as e:
            raise KeyError(f"Missing key {e} in {vote_dict}") from e
