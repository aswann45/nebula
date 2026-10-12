"""Offline tests for bounded, resumable collection."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel

from nebula.collection import (
    CollectionRequest,
    CollectionRunner,
    ExplicitDiscovery,
    ResourceReference,
    RetrievedResource,
)
from nebula.collection.checkpoints import FileCheckpointStore
from nebula.collection.pagination import PaginatedDiscovery, ResourcePage
from nebula.core.exceptions import ConfigurationError
from nebula.storage.filesystem import FilesystemStorage


class Record(BaseModel):
    """Small validated fixture record."""

    value: str


def test_runner_bounds_work_and_resumes_failures(tmp_path: Path) -> None:
    """Persist successes, retry failures, and skip completed resources."""

    async def run() -> None:
        active = 0
        peak = 0
        fetched: list[str] = []
        updates: list[tuple[int, int]] = []
        fail_b = True

        async def fetch(ref: ResourceReference) -> RetrievedResource:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            fetched.append(ref.resource_id)
            try:
                await asyncio.sleep(0.01)
                if ref.resource_id == "b" and fail_b:
                    raise RuntimeError("temporary failure")
                return RetrievedResource(
                    content=ref.resource_id.encode(),
                    source_url=ref.url,
                    retrieved_at=datetime.now(UTC),
                )
            finally:
                active -= 1

        refs = [
            ResourceReference(
                resource_id=name, url=f"https://example.org/{name}"
            )
            for name in ("a", "b", "c")
        ]
        storage = FilesystemStorage(tmp_path / "data")
        checkpoint = FileCheckpointStore(tmp_path / "checkpoint.json")
        request = CollectionRequest(
            source="example",
            collection_id="sample",
            max_concurrency=2,
            preserve_raw=True,
        )
        runner = CollectionRunner(
            request,
            discovery=ExplicitDiscovery(refs),
            fetch=fetch,
            parse=lambda raw: Record(value=raw.decode()),
            storage=storage,
            checkpoint_store=checkpoint,
            progress=lambda completed, total: updates.append(
                (completed, total)
            ),
        )
        first = await runner.run()
        assert (first.discovered, first.attempted, first.successful) == (
            3,
            3,
            2,
        )
        assert first.failed == 1 and peak <= 2
        assert len(first.records) == 2
        assert first.model_dump(mode="json")["records"][0]["value"] == "a"
        assert updates[-1] == (3, 3)
        assert storage.has_record("a")
        assert storage.read_record("a").provenance.content_hash
        assert storage.raw_path("a").read_bytes() == b"a"

        fail_b = False
        resumed = request.model_copy(update={"resume": True})
        second = await CollectionRunner(
            resumed,
            discovery=ExplicitDiscovery(list(reversed(refs))),
            fetch=fetch,
            parse=lambda raw: Record(value=raw.decode()),
            storage=storage,
            checkpoint_store=checkpoint,
        ).run()
        assert (second.attempted, second.successful, second.skipped) == (
            1,
            1,
            2,
        )
        assert fetched.count("a") == fetched.count("c") == 1
        assert fetched.count("b") == 2
        assert second.failed == 0

    asyncio.run(run())


def test_paginated_discovery_does_not_stop_on_empty_page() -> None:
    """Use explicit continuation, even when an intermediate page is empty."""

    async def run() -> None:
        async def fetch(cursor: str | None) -> ResourcePage:
            if cursor is None:
                return ResourcePage(resources=[], next_cursor="next")
            return ResourcePage(
                resources=[
                    ResourceReference(
                        resource_id="one", url="https://example.org/one"
                    )
                ],
                complete=True,
            )

        refs = await PaginatedDiscovery(fetch).discover()
        assert [ref.resource_id for ref in refs] == ["one"]

    asyncio.run(run())


def test_cancelled_collection_keeps_completed_checkpoint(
    tmp_path: Path,
) -> None:
    """Cancellation leaves completed data and checkpoint state intact."""

    async def run() -> None:
        waiting = asyncio.Event()
        release = asyncio.Event()

        async def fetch(ref: ResourceReference) -> RetrievedResource:
            if ref.resource_id == "b":
                waiting.set()
                await release.wait()
            return RetrievedResource(
                content=ref.resource_id.encode(),
                source_url=ref.url,
                retrieved_at=datetime.now(UTC),
            )

        refs = [
            ResourceReference(
                resource_id=name, url=f"https://example.org/{name}"
            )
            for name in ("a", "b")
        ]
        checkpoint = FileCheckpointStore(tmp_path / "checkpoint.json")
        storage = FilesystemStorage(tmp_path / "data")
        task = asyncio.create_task(
            CollectionRunner(
                CollectionRequest(
                    source="example",
                    collection_id="cancel",
                    max_concurrency=1,
                ),
                discovery=ExplicitDiscovery(refs),
                fetch=fetch,
                parse=lambda raw: Record(value=raw.decode()),
                storage=storage,
                checkpoint_store=checkpoint,
            ).run()
        )
        await waiting.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert checkpoint.load().completed_ids == {"a"}
        assert storage.has_record("a")
        assert not storage.has_record("b")

    asyncio.run(run())


def test_checkpoint_rejects_incompatible_request(tmp_path: Path) -> None:
    """Do not resume with changed collection parameters."""

    async def run() -> None:
        checkpoint = FileCheckpointStore(tmp_path / "checkpoint.json")
        first = CollectionRequest(
            source="example",
            collection_id="same",
            parameters={"year": 2026},
        )
        checkpoint.initialize(first)
        changed = first.model_copy(
            update={"resume": True, "parameters": {"year": 2027}}
        )
        with pytest.raises(ConfigurationError, match="incompatible"):
            await CollectionRunner(
                changed,
                discovery=ExplicitDiscovery([]),
                fetch=lambda ref: None,
                parse=lambda raw: Record(value="unused"),
                storage=FilesystemStorage(tmp_path / "data"),
                checkpoint_store=checkpoint,
            ).run()

    asyncio.run(run())
