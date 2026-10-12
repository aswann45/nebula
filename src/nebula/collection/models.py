"""Validated collection requests, results, checkpoints, and provenance."""

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    SerializeAsAny,
)


class ResourceReference(BaseModel):
    """Stable identity and retrieval URL for one published resource."""

    model_config = ConfigDict(frozen=True)

    resource_id: str = Field(min_length=1)
    url: str = Field(min_length=1)


class CollectionRequest(BaseModel):
    """Options that control one repeatable source collection."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    collection_id: str = Field(min_length=1)
    parameters: dict[str, str | int | bool | None] = Field(
        default_factory=dict
    )
    max_concurrency: int = Field(default=5, gt=0)
    parser_version: str = "1"
    resume: bool = False
    overwrite: bool = False
    preserve_raw: bool = False
    retain_records: bool = True

    def fingerprint(self) -> str:
        """Hash the options that change which records a run represents."""
        stable = {
            "source": self.source,
            "collection_id": self.collection_id,
            "parameters": self.parameters,
            "parser_version": self.parser_version,
            "preserve_raw": self.preserve_raw,
        }
        payload = json.dumps(stable, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class CollectionFailure(BaseModel):
    """A resource that could not be fetched, parsed, or persisted."""

    resource_id: str
    error_type: str
    message: str


class CollectionCheckpoint(BaseModel):
    """Durable progress keyed by stable resource identities."""

    source: str
    collection_id: str
    fingerprint: str
    completed_ids: set[str] = Field(default_factory=set)
    filtered_ids: set[str] = Field(default_factory=set)
    failed: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime


class RecordProvenance(BaseModel):
    """Source and retrieval evidence for one stored record."""

    model_config = ConfigDict(frozen=True)

    source: str
    source_url: str
    retrieved_at: datetime
    last_modified: datetime | None = None
    parser_version: str
    collection_id: str
    record_id: str
    content_hash: str


class StoredRecord(BaseModel):
    """Validated record data and its independent provenance."""

    provenance: RecordProvenance
    record: dict[str, JsonValue]


class CollectionResult(BaseModel):
    """Summary of a run, with optional in-memory source records."""

    source: str
    collection_id: str
    started_at: datetime
    completed_at: datetime
    discovered: int = Field(ge=0)
    attempted: int = Field(ge=0)
    successful: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    failures: list[CollectionFailure] = Field(default_factory=list)
    records: list[SerializeAsAny[BaseModel]] = Field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        """Return counters and errors without retaining record payloads."""
        return self.model_dump(mode="json", exclude={"records"})
