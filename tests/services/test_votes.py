"""House vote service tests using local source fixtures."""

import asyncio
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path

import httpx

from nebula.collection.checkpoints import FileCheckpointStore
from nebula.core.config import HTTPConfig
from nebula.house_clerk.client import HouseClerkClient
from nebula.services.votes import VoteService
from nebula.storage.filesystem import FilesystemStorage

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


def test_house_year_collection_partial_failure_and_resume(
    tmp_path: Path,
) -> None:
    """Keep successful votes and retry only the failed roll on resume."""

    async def run() -> None:
        fetched: list[str] = []
        missing = True

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/Votes/MemberVotes":
                return httpx.Response(
                    200,
                    text='<div class="pagination_info">'
                    "1 - 2 of 2 Results</div>"
                    '<a aria-label="Roll number, 3" '
                    'href="/Votes/20263">3</a>'
                    '<a aria-label="Roll number, 1" '
                    'href="/Votes/20261">1</a>',
                )
            fetched.append(request.url.path)
            if request.url.path.endswith("roll001.xml") and missing:
                return httpx.Response(404)
            return httpx.Response(
                200,
                content=(FIXTURES / "house_roll.xml").read_bytes(),
                headers={
                    "Last-Modified": format_datetime(
                        datetime(2026, 9, 1, tzinfo=UTC), usegmt=True
                    )
                },
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = HouseClerkClient(
            http_client=http,
            config=HTTPConfig(max_retries=0, max_concurrency=2),
        )

        async def resolve() -> HouseClerkClient:
            return client

        service = VoteService(resolve)
        storage = FilesystemStorage(tmp_path / "data")
        checkpoint = FileCheckpointStore(tmp_path / "checkpoint.json")
        first = await service.house_year_result(
            2026,
            storage=storage,
            checkpoint_store=checkpoint,
            preserve_raw=True,
            retain_records=False,
        )
        assert (first.successful, first.failed) == (1, 1)
        assert first.records == []
        record = storage.read_record("2026/3")
        assert record.provenance.record_id == "2026/3"
        assert record.provenance.last_modified == datetime(
            2026, 9, 1, tzinfo=UTC
        )
        assert (
            storage.raw_path("2026/3").read_bytes()
            == (FIXTURES / "house_roll.xml").read_bytes()
        )

        missing = False
        second = await service.house_year_result(
            2026,
            storage=storage,
            checkpoint_store=checkpoint,
            resume=True,
            preserve_raw=True,
            retain_records=False,
        )
        assert (second.successful, second.failed, second.skipped) == (1, 0, 1)
        assert fetched.count("/evs/2026/roll003.xml") == 1
        assert fetched.count("/evs/2026/roll001.xml") == 2
        await http.aclose()

    asyncio.run(run())
