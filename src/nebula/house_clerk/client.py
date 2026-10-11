"""Async HTTP client for fetching data from the Clerk of the U.S. House.

Provides access to current member data and roll call vote XML datasets
published by the Clerk's Office. Uses XML parsing and response wrappers
to normalize external data into structured models.
"""

import functools
from datetime import datetime
from typing import Any

import aiometer
import typer
from bs4 import BeautifulSoup as Soup
from httpx import AsyncClient, Response

from nebula.typings import RollCallRequestParams
from nebula.schemas import BaseClient

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
            typer.echo("Fetching current member data from House Clerk...")
            response: Response = await self._perform_request(
                client, "GET", "/xml/lists/MemberData.xml", **kwargs
            )

            return ClerkMemberInfoResponse(
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
                f"/evs/{year}/roll{roll_call_number}.xml",
                **kwargs,
            )
            return ClerkRollCallResponse(
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
                response_json=None,
                year=int(year),
            )
        except self.BASE_ERROR as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    typer.echo(
                        f"Roll call {year} {roll_call_number} not found"
                    )
                else:
                    typer.echo(str(e))
            else:
                typer.echo(str(e))
            return None

    async def get_roll_call_vote_data(
        self,
        roll_call_requests: list[RollCallRequestParams],
    ) -> list[ClerkRollCallResponse | None]:
        """Fetch multiple roll call vote records concurrently.

        Executes batched requests to retrieve XML records for a set of
        roll call vote identifiers. Rate-limited via `aiometer`.

        Parameters
        ----------
        roll_call_requests : list[RollCallRequestParams]
            List of roll call vote parameters, each with `year` and
            `roll_call_number` keys.

        Returns
        -------
        list[ClerkRollCallResponse or None]
            List of structured responses or None for missing records.
        """
        typer.echo(f"Fetching {len(roll_call_requests)} roll calls")
        async with self._client as client:
            tasks = [
                functools.partial(
                    self._get_roll_call_vote,
                    client,
                    year=req["year"],
                    roll_call_number=req["roll_call_number"],
                )
                for req in roll_call_requests
            ]
            results = await aiometer.run_all(tasks, max_per_second=5)
        typer.echo("Finished fetching")
        return results

    async def get_max_roll_call_number(
        self,
        year: int | str,
        **kwargs: Any | None,
    ) -> int:
        """Scrape the maximum roll call number from the EVS index page.

        Loads the Clerk's roll call vote index page for a given year and
        extracts the highest roll call number present in the HTML.

        Parameters
        ----------
        year : int or str
            Year to inspect (e.g., 2024).
        **kwargs : Any, optional
            Optional request arguments for HTTP.

        Returns
        -------
        int
            Maximum roll call number found on the index page.

        Raises
        ------
        Exception
            If the page does not contain a roll call link.
        """
        async with self._client as client:
            response: Response = await self._perform_request(
                client,
                "GET",
                f"/evs/{year}/index.asp",
                **kwargs,
            )
            soup = Soup(response.text, "html.parser")
            roll_call_link = soup.find("a")
            if not roll_call_link:
                raise Exception("Roll call link not found")
            return int(roll_call_link.text.strip())
