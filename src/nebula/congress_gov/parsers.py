"""Offline parsers for Congress.gov JSON responses."""

import json

from pydantic import ValidationError

from nebula.core.exceptions import DataValidationError, ParsingError

from .legislation_models import CongressActionPage, CongressAmendmentPage
from .member_model import Member, MemberResponseModel


def _json_object(content: bytes) -> dict:
    """Decode a Congress.gov JSON object without exposing response data."""
    try:
        data = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParsingError("Invalid Congress.gov JSON") from exc
    if not isinstance(data, dict):
        raise ParsingError("Congress.gov JSON must be an object")
    return data


class CongressActionPageParser:
    """Validate one page of bill or amendment actions."""

    def parse(self, content: bytes) -> CongressActionPage:
        """Return typed actions and pagination from local bytes."""
        try:
            return CongressActionPage.model_validate(_json_object(content))
        except ValidationError as exc:
            raise DataValidationError(
                "Congress.gov actions failed validation"
            ) from exc


class CongressAmendmentPageParser:
    """Validate one page of amendments to a bill."""

    def parse(self, content: bytes) -> CongressAmendmentPage:
        """Return typed amendments and pagination from local bytes."""
        try:
            return CongressAmendmentPage.model_validate(_json_object(content))
        except ValidationError as exc:
            raise DataValidationError(
                "Congress.gov amendments failed validation"
            ) from exc


class CongressGovMemberParser:
    """Parse a Congress.gov member response without HTTP."""

    def parse(self, content: bytes) -> Member:
        """Return the validated member from a JSON response."""
        data = _json_object(content)
        try:
            return MemberResponseModel.model_validate(data).member
        except ValidationError as exc:
            raise DataValidationError(
                "Congress.gov member failed validation"
            ) from exc
