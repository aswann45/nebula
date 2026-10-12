"""OMB service collections use the shared runner and durable storage."""

import asyncio
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path

import httpx
import pytest

from nebula.collection.checkpoints import FileCheckpointStore
from nebula.core.config import HTTPConfig
from nebula.core.exceptions import ResourceNotFoundError
from nebula.omb_apportionments.client import OMBApportionmentsClient
from nebula.services.apportionments import ApportionmentService
from nebula.storage.filesystem import FilesystemStorage

FIXTURE = Path(__file__).parents[1] / "fixtures" / "omb_apportionment.json"


def test_omb_collection_partial_failure_and_resume(tmp_path: Path) -> None:
    """Keep successes and retry only a failed JSON resource."""

    async def run() -> None:
        fetched: list[str] = []
        missing = True

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/":
                return httpx.Response(
                    200,
                    text='<a href="/good.json">good</a>'
                    '<a href="/later.json">later</a>',
                )
            fetched.append(request.url.path)
            if request.url.path == "/later.json" and missing:
                return httpx.Response(404)
            return httpx.Response(
                200,
                content=FIXTURE.read_bytes(),
                headers={
                    "Last-Modified": format_datetime(
                        datetime(2026, 8, 25, tzinfo=UTC), usegmt=True
                    )
                },
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = OMBApportionmentsClient(
            http_client=http, config=HTTPConfig(max_retries=0)
        )

        async def resolve() -> OMBApportionmentsClient:
            return client

        service = ApportionmentService(resolve)
        storage = FilesystemStorage(tmp_path / "data")
        checkpoint = FileCheckpointStore(tmp_path / "checkpoint.json")
        first = await service.collect_result(
            2027,
            storage=storage,
            checkpoint_store=checkpoint,
            preserve_raw=True,
            retain_records=False,
        )
        assert first.successful == 1 and first.failed == 1
        assert first.records == []
        good_id = "https://apportionment-public.max.gov/good.json"
        record = storage.read_record(good_id)
        assert record.record["file_id"] == 11547886
        assert record.provenance.content_hash
        assert record.provenance.record_id == "11547886"
        assert record.provenance.last_modified == datetime(
            2026, 8, 25, tzinfo=UTC
        )
        assert storage.raw_path(good_id).read_bytes() == FIXTURE.read_bytes()

        missing = False
        second = await service.collect_result(
            2027,
            storage=storage,
            checkpoint_store=checkpoint,
            resume=True,
            retain_records=False,
            preserve_raw=True,
        )
        assert (second.successful, second.failed, second.skipped) == (1, 0, 1)
        assert fetched.count("/good.json") == 1
        assert fetched.count("/later.json") == 2
        await http.aclose()

    asyncio.run(run())


def test_omb_collection_reports_missing_index() -> None:
    """A missing index is a source error, not an empty collection."""

    async def run() -> None:
        http = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(404))
        )
        client = OMBApportionmentsClient(
            http_client=http, config=HTTPConfig(max_retries=0)
        )

        async def resolve() -> OMBApportionmentsClient:
            return client

        with pytest.raises(ResourceNotFoundError):
            await ApportionmentService(resolve).collect_result()
        await http.aclose()

    asyncio.run(run())
