"""Async HTTP client for the Congress.gov API.

Provides methods to fetch member data and bill and amendment activity.
Wraps API responses with rich metadata and typed models.
"""

import functools
import json
from collections.abc import Mapping, Sequence
from typing import Any

import aiometer
from httpx import AsyncClient, Response

from nebula.congress_gov.legislation_models import (
    CongressActionPage,
    CongressAmendmentPage,
    CongressAmendmentRequest,
    CongressBillRequest,
)
from nebula.congress_gov.member_model import Member
from nebula.congress_gov.parsers import (
    CongressActionPageParser,
    CongressAmendmentPageParser,
    CongressGovMemberParser,
)
from nebula.congress_gov.schemas import (
    CongressGovMemberResponse,
)
from nebula.core.exceptions import ConfigurationError, ParsingError
from nebula.core.transport import parse_http_date
from nebula.schemas import BaseClient
from nebula.settings import Settings


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
    API_KEY: str | None = None

    def __init__(
        self, *, source_settings: Settings | None = None, **kwargs: Any
    ):
        """Initialize the Congress.gov API client.

        Parameters
        ----------
        **kwargs : Any
            Optional overrides including `API_KEY`.
        source_settings : Settings, optional
            Validated credentials to use instead of loading the environment.

        Raises
        ------
        ConfigurationError
            If no API key is configured.

        """
        key = kwargs.get("API_KEY")
        if key is None:
            configured = (source_settings or Settings()).congress_gov_api_key
            key = configured.get_secret_value() if configured else None
        if not key:
            raise ConfigurationError("Congress.gov API key is not configured")
        kwargs["API_KEY"] = str(key)
        super().__init__(**kwargs)

    async def get_member_model(self, bioguide_id: str) -> Member:
        """Retrieve one member as a validated Congress.gov model."""
        async with self._client as client:
            response = await self._perform_request(
                client,
                "GET",
                f"/member/{bioguide_id}?format=json&api_key={self.API_KEY}",
            )
            return CongressGovMemberParser().parse(response.content)

    async def get_bill_actions(
        self,
        congress: int,
        bill_type: str,
        bill_number: int,
        *,
        offset: int = 0,
        limit: int = 250,
    ) -> CongressActionPage:
        """Retrieve one page of actions taken on a bill."""
        request = CongressBillRequest.model_validate(
            dict(
                congress=congress,
                bill_type=bill_type,
                bill_number=bill_number,
                offset=offset,
                limit=limit,
            )
        )
        content = await self._legislation_content(
            f"/bill/{request.congress}/{request.bill_type}/"
            f"{request.bill_number}/actions",
            request.offset,
            request.limit,
        )
        return CongressActionPageParser().parse(content)

    async def get_bill_amendments(
        self,
        congress: int,
        bill_type: str,
        bill_number: int,
        *,
        offset: int = 0,
        limit: int = 250,
    ) -> CongressAmendmentPage:
        """Retrieve one page of amendments related to a bill."""
        request = CongressBillRequest.model_validate(
            dict(
                congress=congress,
                bill_type=bill_type,
                bill_number=bill_number,
                offset=offset,
                limit=limit,
            )
        )
        content = await self._legislation_content(
            f"/bill/{request.congress}/{request.bill_type}/"
            f"{request.bill_number}/amendments",
            request.offset,
            request.limit,
        )
        return CongressAmendmentPageParser().parse(content)

    async def get_amendment_actions(
        self,
        congress: int,
        amendment_type: str,
        amendment_number: int,
        *,
        offset: int = 0,
        limit: int = 250,
    ) -> CongressActionPage:
        """Retrieve one page of actions taken on an amendment."""
        request = CongressAmendmentRequest.model_validate(
            dict(
                congress=congress,
                amendment_type=amendment_type,
                amendment_number=amendment_number,
                offset=offset,
                limit=limit,
            )
        )
        content = await self._legislation_content(
            f"/amendment/{request.congress}/{request.amendment_type}/"
            f"{request.amendment_number}/actions",
            request.offset,
            request.limit,
        )
        return CongressActionPageParser().parse(content)

    async def _legislation_content(
        self, path: str, offset: int, limit: int
    ) -> bytes:
        """Retrieve a JSON page using the configured API key."""
        async with self._client as client:
            response = await self._perform_request(
                client,
                "GET",
                path,
                params={
                    "format": "json",
                    "api_key": self.API_KEY,
                    "offset": offset,
                    "limit": limit,
                },
            )
            return response.content

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
                last_modified=parse_http_date(
                    response.headers.get("Last-Modified")
                ),
                content_encoding=response.headers.get("Content-Encoding"),
                content_length=response.headers.get("Content-Length"),
                url=str(response.url),
                response_json=response.json(),
            )
        except json.decoder.JSONDecodeError as je:
            raise ParsingError(
                f"Congress.gov returned invalid JSON for member {bioguide_id}"
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
        **kwargs : Any, optional
            Accepted for compatibility; currently unused.

        Returns
        -------
        dict[str, Member]
            Mapping of bioguide ID to parsed `Member` instance.

        """
        async with self._client as client:
            tasks = [
                functools.partial(
                    self._get_single_member_data,
                    client,
                    bioguide_id=b_id,
                )
                for b_id in bioguide_ids
            ]
            results = await aiometer.run_all(
                tasks, max_at_once=self.config.max_concurrency
            )
        return {r.parsed_data.bioguide_id: r.parsed_data for r in results}
