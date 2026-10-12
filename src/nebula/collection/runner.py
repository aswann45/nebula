"""Bounded retrieval, parsing, persistence, and partial-failure handling."""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import BaseModel

from nebula.core.exceptions import ConfigurationError, NebulaError
from nebula.core.transport import safe_url
from nebula.storage.base import RecordStorage

from .checkpoints import FileCheckpointStore
from .models import (
    CollectionCheckpoint,
    CollectionFailure,
    CollectionRequest,
    CollectionResult,
    RecordProvenance,
    ResourceReference,
    StoredRecord,
)
from .pagination import DiscoveryStrategy


@dataclass(frozen=True)
class RetrievedResource:
    """Raw source bytes and factual HTTP retrieval metadata."""

    content: bytes
    source_url: str
    retrieved_at: datetime
    last_modified: datetime | None = None
    content_type: str | None = None


@dataclass
class _RunState:
    queue: asyncio.Queue[tuple[int, ResourceReference]]
    total: int
    skipped: int = 0
    attempted: int = 0
    successful: int = 0
    filtered: int = 0
    records: dict[int, BaseModel] = field(default_factory=dict)
    failures: dict[int, CollectionFailure] = field(default_factory=dict)


class CollectionRunner:
    """Run source-neutral resource retrieval with bounded workers.

    Source adapters supply discovery, retrieval, and parsing. The runner
    handles checkpoint state, retries of failed resources on resume,
    per-record persistence, progress, and error aggregation.
    """

    def __init__(
        self,
        request: CollectionRequest,
        *,
        discovery: DiscoveryStrategy,
        fetch: Callable[
            [ResourceReference], Awaitable[RetrievedResource | None]
        ],
        parse: Callable[[bytes], BaseModel],
        storage: RecordStorage | None = None,
        checkpoint_store: FileCheckpointStore | None = None,
        record_id: Callable[[BaseModel, ResourceReference], str] | None = None,
        include: Callable[[BaseModel], bool] | None = None,
        progress: Callable[[int, int], None] | None = None,
    ) -> None:
        """Compose a collection from source-specific callables."""
        if request.resume and (storage is None or checkpoint_store is None):
            raise ConfigurationError(
                "Resume requires storage and a checkpoint store"
            )
        if request.preserve_raw and storage is None:
            raise ConfigurationError("Raw preservation requires storage")
        if not request.retain_records and storage is None:
            raise ConfigurationError(
                "Persistent storage is required when records are not retained"
            )
        self.request = request
        self.discovery = discovery
        self.fetch = fetch
        self.parse = parse
        self.storage = storage
        self.checkpoint_store = checkpoint_store
        self.record_id = record_id or (lambda model, ref: ref.resource_id)
        self.include = include or (lambda model: True)
        self.progress = progress

    async def run(self) -> CollectionResult:
        """Discover, process, and summarize resources without failing fast."""
        started_at = datetime.now(UTC)
        checkpoint = self._checkpoint()
        discovered = await self.discovery.discover()
        references: list[ResourceReference] = []
        seen: set[str] = set()
        for ref in discovered:
            if ref.resource_id not in seen:
                seen.add(ref.resource_id)
                references.append(ref)
        state = self._state(references, checkpoint)
        async with asyncio.TaskGroup() as group:
            for _ in range(
                min(self.request.max_concurrency, state.queue.qsize())
            ):
                group.create_task(self._worker(state, checkpoint))

        result = CollectionResult(
            source=self.request.source,
            collection_id=self.request.collection_id,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            discovered=state.total,
            attempted=state.attempted,
            successful=state.successful,
            failed=len(state.failures),
            skipped=state.skipped + state.filtered,
            failures=[state.failures[i] for i in sorted(state.failures)],
            records=[state.records[i] for i in sorted(state.records)],
        )
        if self.storage is not None:
            self.storage.write_metadata(result)
        return result

    def _state(
        self,
        references: list[ResourceReference],
        checkpoint: CollectionCheckpoint,
    ) -> _RunState:
        queue: asyncio.Queue[tuple[int, ResourceReference]] = asyncio.Queue()
        state = _RunState(queue=queue, total=len(references))
        for index, ref in enumerate(references):
            completed = ref.resource_id in checkpoint.completed_ids
            filtered = ref.resource_id in checkpoint.filtered_ids
            if self.request.resume and filtered:
                state.skipped += 1
            elif (
                self.request.resume
                and completed
                and self.storage is not None
                and self.storage.has_record(ref.resource_id)
            ):
                state.skipped += 1
            else:
                queue.put_nowait((index, ref))
        return state

    async def _worker(
        self, state: _RunState, checkpoint: CollectionCheckpoint
    ) -> None:
        while True:
            try:
                index, ref = state.queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            state.attempted += 1
            try:
                await self._process(index, ref, state, checkpoint)
            except Exception as exc:
                failure = self._failure(ref, exc)
                state.failures[index] = failure
                checkpoint.failed[ref.resource_id] = failure.error_type
            finally:
                checkpoint.updated_at = datetime.now(UTC)
                if self.checkpoint_store is not None:
                    self.checkpoint_store.save(checkpoint)
                if self.progress is not None:
                    self.progress(
                        state.skipped
                        + state.successful
                        + state.filtered
                        + len(state.failures),
                        state.total,
                    )
                state.queue.task_done()

    async def _process(
        self,
        index: int,
        ref: ResourceReference,
        state: _RunState,
        checkpoint: CollectionCheckpoint,
    ) -> None:
        fetched = await self.fetch(ref)
        if fetched is None:
            raise FileNotFoundError("Resource was not found")
        model = self.parse(fetched.content)
        if not self.include(model):
            checkpoint.filtered_ids.add(ref.resource_id)
            state.filtered += 1
        else:
            self._persist(ref, fetched, model)
            checkpoint.completed_ids.add(ref.resource_id)
            state.successful += 1
            if self.request.retain_records:
                state.records[index] = model
        checkpoint.failed.pop(ref.resource_id, None)

    def _checkpoint(self) -> CollectionCheckpoint:
        if self.checkpoint_store is not None:
            return self.checkpoint_store.initialize(self.request)
        return CollectionCheckpoint(
            source=self.request.source,
            collection_id=self.request.collection_id,
            fingerprint=self.request.fingerprint(),
            updated_at=datetime.now(UTC),
        )

    def _persist(
        self,
        ref: ResourceReference,
        fetched: RetrievedResource,
        model: BaseModel,
    ) -> None:
        if self.storage is None:
            return
        provenance = RecordProvenance(
            source=self.request.source,
            source_url=safe_url(fetched.source_url),
            retrieved_at=fetched.retrieved_at,
            last_modified=fetched.last_modified,
            parser_version=self.request.parser_version,
            collection_id=self.request.collection_id,
            record_id=self.record_id(model, ref),
            content_hash=hashlib.sha256(fetched.content).hexdigest(),
        )
        envelope = StoredRecord(
            provenance=provenance,
            record=model.model_dump(mode="json"),
        )
        self.storage.write_record(
            ref.resource_id,
            envelope,
            raw_content=(
                fetched.content if self.request.preserve_raw else None
            ),
            overwrite=self.request.overwrite,
        )

    @staticmethod
    def _failure(ref: ResourceReference, exc: Exception) -> CollectionFailure:
        message = (
            str(exc) if isinstance(exc, NebulaError) else type(exc).__name__
        )
        return CollectionFailure(
            resource_id=safe_url(ref.resource_id),
            error_type=type(exc).__name__,
            message=message,
        )
