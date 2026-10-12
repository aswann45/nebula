"""Atomic per-resource files and deterministic JSON/JSONL exports."""

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

from pydantic import ValidationError

from nebula.collection.models import CollectionResult, StoredRecord
from nebula.core.exceptions import StorageError


def atomic_write(path: Path, content: bytes, *, overwrite: bool) -> None:
    """Write bytes beside the target and publish them atomically."""
    atomic_stream(
        path, lambda stream: stream.write(content), overwrite=overwrite
    )


def atomic_stream(
    path: Path,
    writer: Callable[[BinaryIO], object],
    *,
    overwrite: bool,
) -> None:
    """Publish a streamed file without exposing partial content."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
    except OSError as exc:
        raise StorageError(f"Could not write {path}: {exc.strerror}") from exc
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            writer(stream)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    except FileExistsError as exc:
        raise StorageError(f"{path} already exists") from exc
    except OSError as exc:
        raise StorageError(f"Could not write {path}: {exc.strerror}") from exc
    finally:
        temporary.unlink(missing_ok=True)


class FilesystemStorage:
    """Store each resource separately under a configurable directory."""

    def __init__(self, directory: Path | str) -> None:
        """Choose a root directory for records, raw bytes, and metadata."""
        self.directory = Path(directory)

    def _key(self, resource_id: str) -> str:
        return hashlib.sha256(resource_id.encode()).hexdigest()

    def record_path(self, resource_id: str) -> Path:
        """Return a deterministic safe path for one parsed record."""
        return self.directory / "records" / f"{self._key(resource_id)}.json"

    def raw_path(self, resource_id: str) -> Path:
        """Return a deterministic safe path for optional raw bytes."""
        return self.directory / "raw" / f"{self._key(resource_id)}.bin"

    def has_record(self, resource_id: str) -> bool:
        """Check that a durable parsed record exists and validates."""
        path = self.record_path(resource_id)
        if not path.is_file():
            return False
        self.read_record(resource_id)
        return True

    def write_record(
        self,
        resource_id: str,
        record: StoredRecord,
        *,
        raw_content: bytes | None = None,
        overwrite: bool = False,
    ) -> None:
        """Write raw content first, then publish a validated record."""
        if raw_content is not None:
            raw_path = self.raw_path(resource_id)
            try:
                existing_raw = raw_path.read_bytes()
            except FileNotFoundError:
                existing_raw = None
            except OSError as exc:
                raise StorageError(
                    "Could not read stored raw content"
                ) from exc
            if existing_raw is not None and not overwrite:
                if existing_raw != raw_content:
                    raise StorageError("Existing raw content differs")
            else:
                atomic_write(raw_path, raw_content, overwrite=overwrite)
        atomic_write(
            self.record_path(resource_id),
            record.model_dump_json().encode(),
            overwrite=overwrite,
        )

    def read_record(self, resource_id: str) -> StoredRecord:
        """Read and validate one persisted record."""
        try:
            return StoredRecord.model_validate_json(
                self.record_path(resource_id).read_bytes()
            )
        except (OSError, ValidationError) as exc:
            raise StorageError("Could not read stored record") from exc

    def write_metadata(self, result: CollectionResult) -> None:
        """Atomically replace the latest collection summary."""
        payload = json.dumps(result.summary(), sort_keys=True).encode()
        atomic_write(
            self.directory / "collection.json", payload, overwrite=True
        )

    def export(
        self,
        output: Path | str,
        *,
        format: str,
        overwrite: bool = False,
    ) -> Path:
        """Export stored envelopes as one JSON or JSONL file."""
        if format not in {"json", "jsonl"}:
            raise ValueError("format must be json or jsonl")
        target = Path(output)
        records = sorted((self.directory / "records").glob("*.json"))

        def write(stream: BinaryIO) -> None:
            if format == "json":
                stream.write(b"[")
            for index, path in enumerate(records):
                if index and format == "json":
                    stream.write(b",")
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(65536), b""):
                        stream.write(chunk)
                if format == "jsonl":
                    stream.write(b"\n")
            if format == "json":
                stream.write(b"]\n")

        atomic_stream(target, write, overwrite=overwrite)
        return target
