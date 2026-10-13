"""House vote service tests using local source fixtures."""

import asyncio
from pathlib import Path

import httpx

from nebula.core.config import HTTPConfig
from nebula.house_clerk.client import HouseClerkClient
from nebula.services.votes import VoteService

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_house_year_skips_missing_rolls() -> None:
    """Use Clerk listing pages and request only published roll numbers."""

    async def run() -> None:
        requested: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested.append(str(request.url))
            if request.url.path == "/Votes/MemberVotes":
                if request.url.params["Page"] == "1":
                    return httpx.Response(
                        200,
                        text='<div class="pagination_info">'
                        "1 - 1 of 2 Results</div>"
                        '<a aria-label="Roll number, 3" '
                        'href="/Votes/20263?Page=2">3</a>',
                    )
                return httpx.Response(
                    200,
                    text='<div class="pagination_info">'
                    "2 - 2 of 2 Results</div>"
                    '<a aria-label="Roll number, 1" '
                    'href="/Votes/20261?Page=3">1</a>',
                )
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
        assert [url.split("?")[0].rsplit("/", 1)[-1] for url in requested] == [
            "MemberVotes",
            "MemberVotes",
            "roll003.xml",
            "roll001.xml",
        ]
        assert "CongressNum=119" in requested[0]
        assert "Session=2nd" in requested[0]
        await http.aclose()

    asyncio.run(run())
