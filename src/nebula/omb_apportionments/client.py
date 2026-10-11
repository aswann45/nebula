"""Async client for retrieving OMB apportionment data.

Connects to the OMB public site, fetches apportionment JSON links from
the main listing page, and loads individual apportionment records in
parallel using TaskGroup and HTTPX.
"""

import asyncio
from datetime import datetime
from typing import Any

from httpx import AsyncClient, Response
import typer

from nebula.schemas import BaseClient

from .schemas import (
    OMBApportionmentsPageResponse,
    OMBSingleApportionmentResponse,
)



class OMBApportionmentsClient(BaseClient):
    """Client for accessing OMB apportionments from MAX.gov.

    Provides methods for scraping the apportionment listing page and
    downloading each individual JSON file using parallelized I/O.

    Attributes
    ----------
    BASE_URL : str
        Root URL hosting apportionment files.
    """

    BASE_URL: str = "https://apportionment-public.max.gov/"

    async def _get_apportionments_page(
        self,
        client: AsyncClient,
        **kwargs: Any | None,
    ) -> OMBApportionmentsPageResponse | None:
        """Fetch the HTML index page listing OMB apportionments.

        Parses the page into a `OMBApportionmentsPageResponse` wrapper
        for extracting downloadable JSON file links.

        Parameters
        ----------
        client : AsyncClient
            Shared HTTPX client used for the request.
        **kwargs : Any, optional
            Optional request arguments.

        Returns
        -------
        OMBApportionmentsPageResponse or None
            Parsed HTML wrapper, or None on failure.
        """
        try:
            response: Response = await self._perform_request(
                client,
                "GET",
                self.BASE_URL,
                **kwargs,
            )
            return OMBApportionmentsPageResponse(
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
        except self.BASE_ERROR as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    pass
                else:
                    typer.echo(str(e))
            else:
                typer.echo(str(e))
            return None

    async def _get_single_apportionment(
        self,
        client: AsyncClient,
        json_link: str,
        **kwargs: Any | None,
    ) -> OMBSingleApportionmentResponse | None:
        """Download a single apportionment JSON file.

        Fetches the file at the given link and parses the response
        into a `OMBSingleApportionmentResponse`.

        Parameters
        ----------
        client : AsyncClient
            Shared HTTPX client used for the request.
        json_link : str
            URL to the specific JSON resource.
        **kwargs : Any, optional
            Optional request arguments.

        Returns
        -------
        OMBSingleApportionmentResponse or None
            Parsed JSON response wrapper, or None on failure.
        """
        try:
            response: Response = await self._perform_request(
                client,
                "GET",
                json_link,
                **kwargs,
            )
            return OMBSingleApportionmentResponse(
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
        except self.BASE_ERROR as e:
            if e.response is not None:
                if e.response.status_code == 404:
                    pass
                else:
                    typer.echo(str(e))
            else:
                typer.echo(str(e))
            return None

    async def get_apportionments_data(
        self,
    ) -> list[OMBSingleApportionmentResponse | None]:
        """Download all available apportionment records in parallel.

        Scrapes the apportionment index page for `.json` links, then uses
        `asyncio.TaskGroup` to fetch all matching JSON files concurrently.

        Returns
        -------
        list[OMBSingleApportionmentResponse or None]
            List of parsed apportionment files (or None if fetch failed).
        """
        async with self._client as client, asyncio.TaskGroup() as tg:
            tasks = []
            json_a_tags = await self._get_apportionments_page(
                client,
            )
            if json_a_tags is None:
                return []
            for a_tag in json_a_tags.parsed_data:
                if isinstance(a_tag["href"], str):
                    task = tg.create_task(
                        self._get_single_apportionment(
                            client,
                            json_link=a_tag["href"],
                        )
                    )
                else:
                    continue
                tasks.append(task)
        return [task.result() for task in tasks]
