"""Congress.gov bill collection with offline paginated responses."""

import asyncio
from pathlib import Path

import httpx
import pytest

from nebula.collection.checkpoints import FileCheckpointStore
from nebula.congress_gov.client import CongressGovClient
from nebula.core.config import HTTPConfig
from nebula.core.exceptions import ParsingError
from nebula.services.legislation import LegislationService
from nebula.storage.filesystem import FilesystemStorage


def test_bill_collection_empty_page_partial_failure_and_resume(
    tmp_path: Path,
) -> None:
    """Follow an empty page and resume by stable bill identity."""

    async def run() -> None:
        missing = True
        reversed_order = False
        fetched: list[str] = []
        base = "https://api.congress.gov/v3/bill/119/hr"

        def listing(offset: int) -> dict:
            first, last = (1, 2) if reversed_order else (2, 1)
            number = first if offset == 0 else last
            bills = (
                []
                if offset == 1
                else [
                    {
                        "congress": 119,
                        "type": "HR",
                        "number": str(number),
                        "title": f"Bill {number}",
                    }
                ]
            )
            next_url = (
                f"{base}?offset={offset + 1}&limit=1&format=json"
                if offset < 2
                else None
            )
            return {
                "bills": bills,
                "pagination": {"count": 2, "next": next_url},
            }

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["api_key"] == "test-key"
            if request.url.path == "/v3/bill/119/hr":
                return httpx.Response(
                    200,
                    json=listing(int(request.url.params["offset"])),
                )
            fetched.append(request.url.path)
            number = int(request.url.path.rsplit("/", 1)[-1])
            if number == 1 and missing:
                return httpx.Response(404)
            return httpx.Response(
                200,
                json={
                    "bill": {
                        "congress": 119,
                        "type": "HR",
                        "number": str(number),
                        "title": f"Bill {number}",
                        "actions": {"count": number},
                    }
                },
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = CongressGovClient(
            API_KEY="test-key",
            http_client=http,
            config=HTTPConfig(max_retries=0, max_concurrency=2),
        )

        async def resolve() -> CongressGovClient:
            return client

        service = LegislationService(resolve)
        storage = FilesystemStorage(tmp_path / "data")
        checkpoint = FileCheckpointStore(tmp_path / "checkpoint.json")
        first = await service.collect_bills_result(
            119,
            "HR",
            page_size=1,
            storage=storage,
            checkpoint_store=checkpoint,
            preserve_raw=True,
            retain_records=False,
        )
        assert (first.discovered, first.successful, first.failed) == (2, 1, 1)
        record = storage.read_record("119/hr/2")
        assert record.record["actions"]["count"] == 2
        assert record.provenance.record_id == "119/hr/2"
        assert "api_key" not in record.provenance.source_url
        assert storage.raw_path("119/hr/2").exists()

        missing = False
        reversed_order = True
        second = await service.collect_bills_result(
            119,
            "hr",
            page_size=1,
            storage=storage,
            checkpoint_store=checkpoint,
            resume=True,
            preserve_raw=True,
            retain_records=False,
        )
        assert (second.discovered, second.successful, second.skipped) == (
            2,
            1,
            1,
        )
        assert fetched.count("/v3/bill/119/hr/2") == 1
        assert fetched.count("/v3/bill/119/hr/1") == 2
        await http.aclose()

    asyncio.run(run())


def test_bill_collection_rejects_untrusted_continuation() -> None:
    """A listing cannot redirect discovery to another host."""

    async def run() -> None:
        http = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "bills": [],
                        "pagination": {
                            "count": 1,
                            "next": "https://other.example/bill?offset=1&limit=1",
                        },
                    },
                )
            )
        )
        client = CongressGovClient(API_KEY="test-key", http_client=http)

        async def resolve() -> CongressGovClient:
            return client

        with pytest.raises(ParsingError):
            await LegislationService(resolve).collect_bills_result(
                119, "hr", page_size=1
            )
        await http.aclose()

    asyncio.run(run())
