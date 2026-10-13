"""Async HTTP client for fetching data from the Clerk of the U.S. House.

Provides access to current member data and roll call vote XML datasets
published by the Clerk's Office. Uses XML parsing and response wrappers
to normalize external data into structured models.
"""

import functools
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import aiometer
from httpx import AsyncClient, Response

from nebula.collection.runner import RetrievedResource
from nebula.core.exceptions import ParsingError, ResourceNotFoundError
from nebula.core.transport import parse_http_date
from nebula.schemas import BaseClient

from .member_model import ClerkData
from .models import HouseRollCall, HouseRollCallRequest
from .parsers import (
    HouseMemberParser,
    HouseRollCallParser,
    HouseVoteListingParser,
)
from .schemas import ClerkMemberInfoResponse, ClerkRollCallResponse


class HouseClerkClient(BaseClient):
    """Client for retrieving data from clerk.house.gov.

    Supports retrieval of current House member metadata, roll call
    voting records, and utility methods for scraping available roll calls.

    Attributes
    ----------
    BASE_URL : str
        Base URL for all requests to the Clerk of the House.

    """

    BASE_URL = "https://clerk.house.gov"

    async def get_current_member_model(self) -> ClerkData:
        """Retrieve the current roster as a validated source model."""
        async with self._client as client:
            response = await self._perform_request(
                client, "GET", "/xml/lists/MemberData.xml"
            )
            return HouseMemberParser().parse(response.content)

    async def get_roll_call_vote_model(
        self, year: int | str, roll_call_number: int | str
    ) -> HouseRollCall | None:
        """Retrieve one roll call as a validated model, or None on 404."""
        request = HouseRollCallRequest(
            year=year, roll_call_number=roll_call_number
        )
        async with self._client as client:
            response = await self._get_roll_call_vote(
                client, request.year, request.roll_call_number
            )
            if response is None or response.text is None:
                return None
            return HouseRollCallParser().parse(response.text.encode())

    def roll_call_url(
        self, year: int | str, roll_call_number: int | str
    ) -> str:
        """Build the published XML URL for a validated roll-call ID."""
        request = HouseRollCallRequest(
            year=year, roll_call_number=roll_call_number
        )
        return (
            f"{self.BASE_URL}/evs/{request.year}/"
            f"roll{request.roll_call_number:03d}.xml"
        )

    async def fetch_roll_call_resource(
        self, year: int | str, roll_call_number: int | str
    ) -> RetrievedResource | None:
        """Retrieve exact roll-call XML bytes and HTTP provenance."""
        url = self.roll_call_url(year, roll_call_number)
        async with self._client as client:
            try:
                response = await self._perform_request(client, "GET", url)
            except ResourceNotFoundError:
                return None
            return RetrievedResource(
                content=response.content,
                source_url=str(response.url),
                retrieved_at=datetime.now(UTC),
                last_modified=parse_http_date(
                    response.headers.get("Last-Modified")
                ),
                content_type=response.headers.get("Content-Type"),
            )

    async def get_current_member_data(
        self, **kwargs: Any | None
    ) -> ClerkMemberInfoResponse:
        """Fetch the full House member roster from the Clerk's XML feed.

        Loads `/xml/lists/MemberData.xml` and parses it into a structured
        `ClerkMemberInfoResponse`.

        Parameters
        ----------
        **kwargs : Any, optional
            Optional request arguments passed to the underlying HTTP call.

        Returns
        -------
        ClerkMemberInfoResponse
            Parsed and structured response including member metadata.

        """
        async with self._client as client:
            response: Response = await self._perform_request(
                client, "GET", "/xml/lists/MemberData.xml", **kwargs
            )

            return ClerkMemberInfoResponse(
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

    async def _get_roll_call_vote(
        self,
        client: AsyncClient,
        year: int | str,
        roll_call_number: str | int,
        **kwargs: Any | None,
    ) -> ClerkRollCallResponse | None:
        """Fetch an individual roll call vote from the Clerk's archive.

        Retrieves a single vote record as XML from the `/evs/` path and
        wraps it into a structured response object.

        Parameters
        ----------
        client : AsyncClient
            HTTPX client for reuse across calls.
        year : int or str
            Year of the vote (e.g., 2023).
        roll_call_number : int or str
            Specific roll call number to retrieve.
        **kwargs : Any, optional
            Extra request options.

        Returns
        -------
        ClerkRollCallResponse or None
            Structured response if successful, or None if not found (404).

        """
        try:
            response: Response = await self._perform_request(
                client,
                "GET",
                self.roll_call_url(year, roll_call_number),
                **kwargs,
            )
            return ClerkRollCallResponse(
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
                year=int(year),
            )
        except ResourceNotFoundError:
            return None

    async def get_roll_call_vote_data(
        self,
        roll_call_requests: Sequence[
            HouseRollCallRequest | Mapping[str, str | int]
        ],
    ) -> list[ClerkRollCallResponse | None]:
        """Fetch multiple roll call vote records concurrently.

        Executes batched requests to retrieve XML records for a set of
        roll call vote identifiers. Rate-limited via `aiometer`.

        Parameters
        ----------
        roll_call_requests : sequence of HouseRollCallRequest or mappings
            List of roll call vote parameters, each with `year` and
            `roll_call_number` keys.

        Returns
        -------
        list[ClerkRollCallResponse or None]
            List of structured responses or None for missing records.

        """
        requests = [
            HouseRollCallRequest.model_validate(req)
            for req in roll_call_requests
        ]
        async with self._client as client:
            tasks = [
                functools.partial(
                    self._get_roll_call_vote,
                    client,
                    year=req.year,
                    roll_call_number=req.roll_call_number,
                )
                for req in requests
            ]
            results = await aiometer.run_all(
                tasks,
                max_at_once=self.config.max_concurrency,
                max_per_second=5,
            )
        return results

    async def list_roll_call_numbers(self, year: int | str) -> list[int]:
        """List roll numbers published for a House voting year.

        The Clerk's vote search provides paginated results; the old
        ``/evs/{year}/index.asp`` archive index is unavailable.
        """
        voting_year = int(year)
        if voting_year < 1935:
            raise ValueError("House vote listing requires year 1935 or later")
        congress = (voting_year - 1789) // 2 + 1
        session = "1st" if voting_year % 2 else "2nd"
        parser = HouseVoteListingParser()
        numbers: list[int] = []
        seen: set[int] = set()
        async with self._client as client:
            for page in range(1, 1001):
                response = await self._perform_request(
                    client,
                    "GET",
                    "/Votes/MemberVotes",
                    params={
                        "CongressNum": congress,
                        "Session": session,
                        "Page": page,
                    },
                )
                current, has_next = parser.parse(response.content, voting_year)
                for number in current:
                    if number not in seen:
                        numbers.append(number)
                        seen.add(number)
                if not has_next:
                    return numbers
        raise ParsingError("House vote listing exceeded 1000 pages")

    async def get_max_roll_call_number(
        self,
        year: int | str,
        **kwargs: Any | None,
    ) -> int:
        """Return the highest roll number in the Clerk's vote listing.

        Parameters
        ----------
        year : int or str
            Year to inspect (e.g., 2024).
        **kwargs : Any, optional
            Accepted for compatibility.

        Returns
        -------
        int
            Maximum roll call number found on the index page.

        Raises
        ------
        ParsingError
            If the page does not contain a recognizable roll-call link.

        """
        numbers = await self.list_roll_call_numbers(year)
        if not numbers:
            raise ParsingError("House vote listing has no roll calls")
        return max(numbers)
