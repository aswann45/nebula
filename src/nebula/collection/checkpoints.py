"""Durable collection checkpoints with compatibility validation."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from nebula.core.exceptions import ConfigurationError, StorageError
from nebula.storage.filesystem import atomic_write

from .models import CollectionCheckpoint, CollectionRequest


class FileCheckpointStore:
    """Persist one collection checkpoint as an atomic JSON file."""

    def __init__(self, path: Path | str) -> None:
        """Choose the checkpoint destination."""
        self.path = Path(path)

    def load(self) -> CollectionCheckpoint | None:
        """Read an existing checkpoint if present."""
        if not self.path.exists():
            return None
        try:
            return CollectionCheckpoint.model_validate_json(
                self.path.read_bytes()
            )
        except (OSError, ValidationError) as exc:
            raise StorageError("Could not read collection checkpoint") from exc

    def initialize(self, request: CollectionRequest) -> CollectionCheckpoint:
        """Create or validate progress for a new or resumed run."""
        existing = self.load()
        if request.resume and existing is not None:
            if existing.fingerprint != request.fingerprint():
                raise ConfigurationError(
                    "Checkpoint is incompatible with request"
                )
            return existing
        if existing is not None and not request.overwrite:
            raise StorageError(
                "Checkpoint exists; use resume or explicit overwrite"
            )
        checkpoint = CollectionCheckpoint(
            source=request.source,
            collection_id=request.collection_id,
            fingerprint=request.fingerprint(),
            updated_at=datetime.now(UTC),
        )
        self.save(checkpoint)
        return checkpoint

    def save(self, checkpoint: CollectionCheckpoint) -> None:
        """Safely replace checkpoint state after a completed resource."""
        data = checkpoint.model_dump(mode="json")
        data["completed_ids"] = sorted(checkpoint.completed_ids)
        data["filtered_ids"] = sorted(checkpoint.filtered_ids)
        payload = json.dumps(data, sort_keys=True).encode()
        atomic_write(self.path, payload, overwrite=True)
