"""Offline YAML parsers for GitHub congressional datasets."""

from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from nebula.core.exceptions import DataValidationError, ParsingError

from .models import GitHubCommittee, GitHubMember

T = TypeVar("T", bound=BaseModel)


def _records(content: bytes, model: type[T]) -> list[T]:
    try:
        data = yaml.safe_load(content)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ParsingError("Invalid congressional YAML") from exc
    if not isinstance(data, list):
        raise ParsingError("Congressional YAML must contain a list")
    try:
        return [model.model_validate(item) for item in data]
    except ValidationError as exc:
        raise DataValidationError(
            "Congressional YAML failed validation"
        ) from exc


class GitHubMemberParser:
    """Parse current legislators into source-specific models."""

    def parse(self, content: bytes) -> list[GitHubMember]:
        """Validate a current legislator YAML file."""
        return _records(content, GitHubMember)


class GitHubHistoricalMemberParser:
    """Parse historical legislators into dated source records."""

    def parse(self, content: bytes) -> list[GitHubMember]:
        """Validate a historical legislator YAML file."""
        return _records(content, GitHubMember)


class GitHubCommitteeParser:
    """Parse congressional committee YAML into typed records."""

    def parse(self, content: bytes) -> list[GitHubCommittee]:
        """Validate current committee YAML content."""
        return _records(content, GitHubCommittee)
