"""Async client for retrieving OMB apportionment data.

Connects to the OMB public site, fetches apportionment JSON links from
the main listing page, and loads individual apportionment records in
parallel using TaskGroup and HTTPX.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

from httpx import AsyncClient, Response

from nebula.collection.runner import RetrievedResource
from nebula.core.exceptions import (
    ConfigurationError,
    RequestError,
    ResourceNotFoundError,
)
from nebula.core.transport import parse_http_date
from nebula.schemas import BaseClient

from .models import OMBApportionment, OMBApportionmentReference
from .parsers import (
    OMBApportionmentParser,
    OMBApportionmentReferenceParser,
)
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

    async def list_apportionment_references(
        self,
    ) -> list[OMBApportionmentReference]:
        """Return validated OMB JSON links in index order."""
        async with self._client as client:
            page = await self._get_apportionments_page(client)
            if page is None or page.text is None:
                return []
            return OMBApportionmentReferenceParser(self.BASE_URL).parse(
                page.text.encode()
            )

    async def get_apportionment_model(
        self, url: str
    ) -> OMBApportionment | None:
        """Retrieve one JSON resource as a validated OMB model."""
        fetched = await self.fetch_resource(url)
        if fetched is None:
            return None
        return OMBApportionmentParser().parse(fetched.content)

    async def get_index_content(self) -> bytes:
        """Retrieve raw HTML for independent index discovery."""
        async with self._client as client:
            response = await self._perform_request(
                client, "GET", self.BASE_URL
            )
            return response.content

    async def fetch_resource(self, url: str) -> RetrievedResource | None:
        """Retrieve exact JSON bytes and HTTP provenance for collection."""
        parts = urlsplit(urljoin(self.BASE_URL, url))
        if (
            parts.scheme != "https"
            or parts.hostname != urlsplit(self.BASE_URL).hostname
            or not parts.path.lower().endswith(".json")
        ):
            raise ConfigurationError("Invalid OMB JSON resource URL")
        async with self._client as client:
            try:
                response = await self._perform_request(
                    client, "GET", parts.geturl()
                )
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
                last_modified=parse_http_date(
                    response.headers.get("Last-Modified")
                ),
                content_encoding=response.headers.get("Content-Encoding"),
                content_length=response.headers.get("Content-Length"),
                url=str(response.url),
                response_json=None,
            )
        except ResourceNotFoundError:
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
                last_modified=parse_http_date(
                    response.headers.get("Last-Modified")
                ),
                content_encoding=response.headers.get("Content-Encoding"),
                content_length=response.headers.get("Content-Length"),
                url=str(response.url),
                response_json=None,
            )
        except ResourceNotFoundError:
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
            List of parsed apportionment files (or None if missing).

        """
        async with self._client as client:
            page = await self._get_apportionments_page(client)
            if page is None:
                return []
            links: list[str] = []
            seen: set[str] = set()
            permitted_host = urlsplit(self.BASE_URL).hostname
            for tag in page.parsed_data:
                href = tag.get("href")
                if not isinstance(href, str):
                    continue
                url = urljoin(self.BASE_URL, href)
                parts = urlsplit(url)
                if (
                    parts.hostname != permitted_host
                    or not parts.path.lower().endswith(".json")
                    or url in seen
                ):
                    continue
                seen.add(url)
                links.append(url)

            results: list[OMBSingleApportionmentResponse | None] = [
                None
            ] * len(links)
            positions = iter(enumerate(links))

            async def worker() -> None:
                for index, url in positions:
                    results[index] = await self._get_single_apportionment(
                        client, json_link=url
                    )

            try:
                async with asyncio.TaskGroup() as group:
                    for _ in range(
                        min(self.config.max_concurrency, len(links))
                    ):
                        group.create_task(worker())
            except* RequestError as failures:
                raise failures.exceptions[0] from None
            return results
