"""Async HTTP client for the Congress.gov API.

Provides methods to fetch member data and (placeholder) endpoints for
bill and amendment activity. Wraps API responses with rich metadata and
typed models.
"""

import functools
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

import aiometer
import typer
from httpx import AsyncClient, Response

from nebula.settings import settings
from nebula.congress_gov.member_model import Member
from nebula.congress_gov.schemas import (
    CongressGovMemberResponse,
)
from nebula.schemas import BaseClient


class CongressGovClient(BaseClient):
    """Client for accessing Congress.gov REST API endpoints.

    Handles request signing, concurrency, and structured response
    parsing. Fetches Member profiles and prepares typed outputs
    for downstream use.

    Attributes
    ----------
    API_VERSION : str
        Version of the Congress.gov API to target.
    BASE_URL : str
        Full base URL including API version.
    API_KEY : str
        API key used for authentication (from app settings).
    """

    API_VERSION = "v3"
    BASE_URL = f"https://api.congress.gov/{API_VERSION}"
    API_KEY = settings.congress_gov_api_key

    def __init__(self, **kwargs: Any | None):
        """Initialize the Congress.gov API client.

        Parameters
        ----------
        **kwargs : Any
            Optional overrides including `API_KEY`.

        Raises
        ------
        ValueError
            If `API_KEY` is missing or placeholder value is used.
        """
        if "API_KEY" in kwargs:
            self.API_KEY = str(kwargs["API_KEY"])
        if self.API_KEY == "changethis":
            raise ValueError(
                "API key not found. Did you set it in the app settings?"
            )
        super().__init__(**kwargs)

    async def get_bill_actions(
        self, **kwargs: Any | None
    ) -> None:  # -> CongressGovResponse:
        """Fetch actions taken on a bill. [Placeholder]."""
        pass

    async def get_bill_amendments(
        self, **kwargs: Any | None
    ) -> None:  # -> CongressGovResponse:
        """Fetch amendments related to a bill. [Placeholder]."""
        pass

    async def get_amendment_actions(
        self, **kwargs: Any | None
    ) -> None:  # -> CongressGovResponse:
        """Fetch actions taken on a specific amendment. [Placeholder]."""
        pass

    async def _get_single_member_data(
        self, client: AsyncClient, bioguide_id: str, **kwargs: Any | None
    ) -> CongressGovMemberResponse:
        """Fetch and parse data for a single Member of Congress.

        Parameters
        ----------
        client : AsyncClient
            HTTPX client instance (shared across tasks).
        bioguide_id : str
            Unique bioguide identifier for the Member.
        **kwargs : Any
            Reserved for future use.

        Returns
        -------
        CongressGovMemberResponse
            Parsed and enriched API response for the Member.
        """
        response: Response = await self._perform_request(
            client,
            "GET",
            f"/member/{bioguide_id}?format=json&api_key={self.API_KEY}",
        )

        try:
            return CongressGovMemberResponse(
                text=response.text,
                encoding=response.encoding,
                content_type=response.headers.get("Content-Type"),
                last_modified=(
                    datetime.strptime(
                        modified,
                        "%a, %d %b %Y %H:%M:%S %Z",
                    )
                    if (modified := response.headers.get("Last-Modified"))
                    else None
                ),
                content_encoding=response.headers.get("Content-Encoding"),
                content_length=response.headers.get("Content-Length"),
                url=str(response.url),
                response_json=response.json(),
            )
        except json.decoder.JSONDecodeError as je:
            raise RuntimeError(
                f"JSON decode failed for the following request:\n"
                f"bioguide_id: {bioguide_id}; api_key: {self.API_KEY}"
            ) from je

    async def get_member_data(
        self, bioguide_ids: Sequence[str], **kwargs: Any | None
    ) -> Mapping[str, Member]:
        """Fetch data for multiple Members of Congress in parallel.

        Uses `aiometer` to dispatch concurrent requests and parse
        results into `Member` models.

        Parameters
        ----------
        bioguide_ids : Sequence[str]
            List of bioguide IDs to fetch.

        Returns
        -------
        dict[str, Member]
            Mapping of bioguide ID to parsed `Member` instance.
        """
        typer.echo(f"Fetching {len(bioguide_ids)} Members' data")
        async with self._client as client:
            tasks = [
                functools.partial(
                    self._get_single_member_data,
                    client,
                    bioguide_id=b_id,
                )
                for b_id in bioguide_ids
            ]
            results = await aiometer.run_all(tasks)
        typer.echo("Finished fetching")
        return {r.parsed_data.bioguide_id: r.parsed_data for r in results}
