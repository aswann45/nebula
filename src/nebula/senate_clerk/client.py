"""Async client for retrieving Senate member roster data from senate.gov.

Connects to the LIS endpoint at `/legislative/LIS_MEMBER/cvc_member_data.xml`,
parses the XML response, and returns structured models via Pydantic wrappers.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from httpx import Response

from nebula.schemas import BaseClient
from nebula.senate_clerk.schemas import (
    ClerkSenatorInfoResponse,
)


class SenateClerkClient(BaseClient):
    """Client for accessing current Senate membership data from senate.gov.

    Connects to the Clerk's official XML endpoint for retrieving structured
    data on sitting U.S. Senators, including committee assignments and office
    metadata.

    Attributes
    ----------
    BASE_URL : str
        Root domain for all Clerk-related API requests.
    """

    BASE_URL = "https://www.senate.gov"

    async def get_current_member_data(
        self, **kwargs: Any | None
    ) -> ClerkSenatorInfoResponse:
        """Fetch the current Senate member roster from the LIS XML feed.

        Loads the `/legislative/LIS_MEMBER/cvc_member_data.xml` endpoint and
        returns a parsed response as a structured `ClerkSenatorInfoResponse`.

        Parameters
        ----------
        **kwargs : Any, optional
            Additional request parameters for the internal HTTP call.

        Returns
        -------
        ClerkSenatorInfoResponse
            Parsed and validated member roster data.
        """
        async with self._client as client:
            typer.echo("Fetching current member data from Senate...")
            response: Response = await self._perform_request(
                client,
                "GET",
                "/legislative/LIS_MEMBER/cvc_member_data.xml",
                **kwargs,
            )

            return ClerkSenatorInfoResponse(
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


if __name__ == "__main__":
    client = SenateClerkClient()
    data = asyncio.run(client.get_current_member_data())
    with open(Path().home() / "senate_clerk_data.json", "w") as f:
        json.dump(data.parsed_data, f)
