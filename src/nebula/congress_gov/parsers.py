"""Offline parser for Congress.gov member JSON responses."""

import json

from pydantic import ValidationError

from nebula.core.exceptions import DataValidationError, ParsingError

from .member_model import Member, MemberResponseModel


class CongressGovMemberParser:
    """Parse a Congress.gov member response without HTTP."""

    def parse(self, content: bytes) -> Member:
        """Return the validated member from a JSON response."""
        try:
            data = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParsingError("Invalid Congress.gov member JSON") from exc
        try:
            return MemberResponseModel.model_validate(data).member
        except ValidationError as exc:
            raise DataValidationError(
                "Congress.gov member failed validation"
            ) from exc
