"""Offline XML parser for the Senate Clerk member roster."""

from typing import Any

import xmltodict
from pydantic import ValidationError

from nebula.core.exceptions import DataValidationError, ParsingError

from .member_model import ClerkData


class SenateMemberParser:
    """Parse and validate the Senate's published member roster."""

    def parse(self, content: bytes) -> ClerkData:
        """Parse Senate XML without network or response metadata."""
        try:
            data: Any = xmltodict.parse(content)
        except Exception as exc:
            raise ParsingError("Invalid Senate Clerk XML") from exc
        try:
            return ClerkData.model_validate(data)
        except ValidationError as exc:
            raise DataValidationError(
                "Senate member roster failed validation"
            ) from exc
