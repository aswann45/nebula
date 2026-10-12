"""Offline parsers for OMB JSON records and HTML discovery."""

import json
from decimal import Decimal
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
from pydantic import ValidationError

from nebula.core.exceptions import DataValidationError, ParsingError

from .models import OMBApportionment, OMBApportionmentReference


class OMBApportionmentParser:
    """Parse an OMB JSON document into a validated record."""

    def parse(self, content: bytes) -> OMBApportionment:
        """Parse bytes locally, validating whole monetary amounts."""
        try:
            data = json.loads(content, parse_float=Decimal)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParsingError("Invalid OMB JSON document") from exc
        if not isinstance(data, dict):
            raise ParsingError("OMB JSON document must be an object")
        try:
            return OMBApportionment.model_validate(data)
        except ValidationError as exc:
            raise DataValidationError(
                "OMB JSON document failed validation"
            ) from exc


class OMBApportionmentReferenceParser:
    """Discover same-host JSON links from an OMB index page."""

    def __init__(self, base_url: str) -> None:
        """Use the source URL as the only permitted host."""
        self.base_url = base_url
        self.permitted_host = urlsplit(base_url).hostname

    def parse(self, content: bytes) -> list[OMBApportionmentReference]:
        """Resolve, validate, deduplicate, and order JSON references."""
        try:
            soup = BeautifulSoup(content, "html.parser")
        except (UnicodeDecodeError, ValueError) as exc:
            raise ParsingError("Invalid OMB index HTML") from exc
        references: list[OMBApportionmentReference] = []
        seen: set[str] = set()
        for tag in soup.find_all("a", href=True):
            href = tag.get("href")
            if not isinstance(href, str):
                continue
            url = urljoin(self.base_url, href)
            parts = urlsplit(url)
            if (
                parts.scheme != "https"
                or parts.hostname != self.permitted_host
                or not parts.path.lower().endswith(".json")
                or url in seen
            ):
                continue
            seen.add(url)
            references.append(
                OMBApportionmentReference(
                    url=url,
                    file_name=unquote(parts.path.rsplit("/", 1)[-1]),
                )
            )
        return references
