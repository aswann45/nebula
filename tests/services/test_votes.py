"""House vote service tests using local source fixtures."""

import asyncio
from pathlib import Path

import httpx

from nebula.core.config import HTTPConfig
from nebula.house_clerk.client import HouseClerkClient
from nebula.services.votes import VoteService

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_house_year_skips_missing_rolls() -> None:
    """Continue through gaps in listed roll-call numbers."""

    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("index.asp"):
                return httpx.Response(
                    200,
                    text='<a href="/help">2026</a>'
                    '<a href="roll003.xml">3</a>'
                    '<a href="roll001.xml">1</a>',
                )
            if request.url.path.endswith("roll002.xml"):
                return httpx.Response(404)
            return httpx.Response(
                200, content=(FIXTURES / "house_roll.xml").read_bytes()
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = HouseClerkClient(
            http_client=http,
            config=HTTPConfig(max_retries=0, max_concurrency=2),
        )

        async def resolve() -> HouseClerkClient:
            return client

        votes = await VoteService(resolve).house_year(2026)
        assert len(votes) == 2
        await http.aclose()

    asyncio.run(run())
