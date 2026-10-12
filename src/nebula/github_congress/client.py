"""Async HTTP client for fetching structured congressional data from GitHub.

Wraps calls to the `unitedstates/congress-legislators` repository,
retrieving current and historical member and committee records in YAML format.
"""

from typing import Any

from httpx import Response

from nebula.core.transport import parse_http_date
from nebula.schemas import BaseClient

from .models import (
    GitHubCommittee,
    GitHubHistoricalMembersRequest,
    GitHubMember,
)
from .parsers import (
    GitHubCommitteeParser,
    GitHubHistoricalMemberParser,
    GitHubMemberParser,
)
from .schemas import (
    GHCCurrentCommitteeResponse,
    GHCCurrentMemberResponse,
    GHCHistoricalMemberResponse,
)


class GitHubCongressClient(BaseClient):
    """Client for accessing YAML-based congressional datasets from GitHub.

    Connects to the `unitedstates/congress-legislators` public repository and
    retrieves metadata about current and historical Members of Congress and
    committees. All responses are parsed using YAML-aware schemas.

    Attributes
    ----------
    BASE_URL : str
        Base path to the GitHub-hosted static files.
    """

    BASE_URL = (
        "https://raw.githubusercontent.com/unitedstates/"
        "congress-legislators/main"
    )

    async def get_current_members(self) -> list[GitHubMember]:
        """Retrieve current legislators as validated source models."""
        async with self._client as client:
            response = await self._perform_request(
                client, "GET", "/legislators-current.yaml"
            )
            return GitHubMemberParser().parse(response.content)

    async def get_current_committees(self) -> list[GitHubCommittee]:
        """Retrieve current committees as validated source models."""
        async with self._client as client:
            response = await self._perform_request(
                client, "GET", "/committees-current.yaml"
            )
            return GitHubCommitteeParser().parse(response.content)

    async def get_historical_members(
        self, year: int | str
    ) -> list[GitHubMember]:
        """Retrieve historical members whose last term reaches a year."""
        minimum_year = GitHubHistoricalMembersRequest(year=year).year
        async with self._client as client:
            response = await self._perform_request(
                client, "GET", "/legislators-historical.yaml"
            )
            members = GitHubHistoricalMemberParser().parse(response.content)
            return [
                member
                for member in members
                if member.terms[-1].end.year >= minimum_year
            ]

    async def get_current_member_data(
        self, **kwargs: Any | None
    ) -> GHCCurrentMemberResponse:
        """Fetch current Members of Congress from GitHub.

        Loads `legislators-current.yaml` and returns a parsed response model.

        Parameters
        ----------
        **kwargs : Any
            Optional arguments forwarded to the HTTP client.

        Returns
        -------
        GHCCurrentMemberResponse
            Structured response containing current member metadata.
        """
        async with self._client as client:
            response: Response = await self._perform_request(
                client, "GET", "/legislators-current.yaml", **kwargs
            )
            return GHCCurrentMemberResponse(
                text=response.text,
                encoding=response.encoding,
                content_type=response.headers.get("Content-Type"),
                last_modified=parse_http_date(
                    response.headers.get("Last-Modified")
                ),
                content_encoding=response.headers.get("Content-Encoding"),
                content_length=response.headers.get("Content-Length"),
                url=str(response.url),
                response_json=None,
            )

    async def get_current_committee_data(
        self, **kwargs: Any | None
    ) -> GHCCurrentCommitteeResponse:
        """Fetch current congressional committee data.

        Loads `committees-current.yaml` and returns parsed content.

        Parameters
        ----------
        **kwargs : Any
            Optional arguments passed to the request.

        Returns
        -------
        GHCCurrentCommitteeResponse
            Structured response for current committee metadata.
        """
        async with self._client as client:
            response: Response = await self._perform_request(
                client, "GET", "/committees-current.yaml", **kwargs
            )
            return GHCCurrentCommitteeResponse(
                text=response.text,
                encoding=response.encoding,
                content_type=response.headers.get("Content-Type"),
                last_modified=parse_http_date(
                    response.headers.get("Last-Modified")
                ),
                content_encoding=response.headers.get("Content-Encoding"),
                content_length=response.headers.get("Content-Length"),
                url=str(response.url),
                response_json=None,
            )

    async def get_historical_member_data(
        self, year: int | str, **kwargs: Any | None
    ) -> GHCHistoricalMemberResponse:
        """Fetch historical Member records with year-based filtering.

        Loads `legislators-historical.yaml` and returns only those
        Members who served during or after the specified year.

        Parameters
        ----------
        year : int or str
            Minimum service year for inclusion.
        **kwargs : Any
            Optional overrides for HTTP request parameters.

        Returns
        -------
        GHCHistoricalMemberResponse
            Parsed response model filtered by the `year` argument.
        """
        async with self._client as client:
            response: Response = await self._perform_request(
                client, "GET", "/legislators-historical.yaml", **kwargs
            )
            return GHCHistoricalMemberResponse(
                text=response.text,
                encoding=response.encoding,
                content_type=response.headers.get("Content-Type"),
                last_modified=parse_http_date(
                    response.headers.get("Last-Modified")
                ),
                content_encoding=response.headers.get("Content-Encoding"),
                content_length=response.headers.get("Content-Length"),
                url=str(response.url),
                response_json=None,
                year=year,
            )
