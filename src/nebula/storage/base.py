"""Storage contract used by the reusable collection runner."""

from typing import Protocol

from nebula.collection.models import CollectionResult, StoredRecord


class RecordStorage(Protocol):
    """Persist independent records and collection metadata."""

    def has_record(self, resource_id: str) -> bool:
        """Return whether a resource has a durable parsed record."""
        ...

    def write_record(
        self,
        resource_id: str,
        record: StoredRecord,
        *,
        raw_content: bytes | None = None,
        overwrite: bool = False,
    ) -> None:
        """Persist one record, optionally including source bytes."""
        ...

    def write_metadata(self, result: CollectionResult) -> None:
        """Persist collection-level counters and failures."""
        ...
