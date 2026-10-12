"""Offline XML parsers for House Clerk rosters and votes."""

from datetime import datetime
from typing import Any

import xmltodict
from pydantic import ValidationError

from nebula.core.exceptions import DataValidationError, ParsingError

from .member_model import ClerkData
from .models import HouseRollCall


def _xml(content: bytes) -> dict[str, Any]:
    try:
        result = xmltodict.parse(content, attr_prefix="", cdata_key="text")
    except Exception as exc:
        raise ParsingError("Invalid House Clerk XML") from exc
    if not isinstance(result, dict):
        raise ParsingError("House Clerk XML has no root element")
    return result


class HouseMemberParser:
    """Parse a published House member roster without HTTP."""

    def parse(self, content: bytes) -> ClerkData:
        """Validate XML content against the Clerk roster model."""
        try:
            return ClerkData.model_validate(_xml(content))
        except ValidationError as exc:
            raise DataValidationError(
                "House member roster failed validation"
            ) from exc


class HouseRollCallParser:
    """Parse a House roll-call XML document into typed records."""

    def parse(self, content: bytes) -> HouseRollCall:
        """Validate vote metadata and all recorded member positions."""
        document = _xml(content)
        try:
            root = document["rollcall-vote"]
            metadata = root["vote-metadata"]
            entries = root["vote-data"]["recorded-vote"]
            if isinstance(entries, dict):
                entries = [entries]
            if not isinstance(entries, list):
                raise TypeError("recorded-vote must be a list")
            date = datetime.strptime(
                metadata["action-date"], "%d-%b-%Y"
            ).date()
            data = {
                "congress": metadata["congress"],
                "session": metadata["session"],
                "chamber": "House",
                "roll_call_number": metadata["rollcall-num"],
                "bill_number": metadata.get("legis-num"),
                "vote_question": metadata["vote-question"],
                "vote_description": metadata.get("vote-desc"),
                "vote_type": metadata["vote-type"],
                "vote_result": metadata["vote-result"],
                "action_date": date,
                "majority": metadata.get("majority"),
                "amendment_author": metadata.get("amendment-author"),
                "amendment_number_offered": metadata.get("amendment-num"),
                "year": date.year,
                "source_metadata": metadata,
                "votes": [
                    {
                        "bioguide_id": item["legislator"]["name-id"],
                        "vote": item["vote"],
                        "party": item["legislator"].get("party"),
                        "member_last_name": item["legislator"].get("text"),
                        "source_record": item,
                    }
                    for item in entries
                ],
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise ParsingError("Invalid House roll-call structure") from exc
        try:
            return HouseRollCall.model_validate(data)
        except ValidationError as exc:
            raise DataValidationError(
                "House roll call failed validation"
            ) from exc
