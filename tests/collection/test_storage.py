"""Filesystem record export and overwrite behavior."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nebula.collection.models import RecordProvenance, StoredRecord
from nebula.core.exceptions import StorageError
from nebula.storage.filesystem import FilesystemStorage


def test_json_jsonl_export_and_overwrite(tmp_path: Path) -> None:
    """Export validated envelopes without losing provenance or fields."""
    storage = FilesystemStorage(tmp_path / "store")
    envelope = StoredRecord(
        provenance=RecordProvenance(
            source="example",
            source_url="https://example.org/one",
            retrieved_at=datetime.now(UTC),
            parser_version="1",
            collection_id="sample",
            record_id="one",
            content_hash="abc",
        ),
        record={"name": "One", "nested": {"a": [1, 2]}},
    )
    storage.write_record("one", envelope)
    with pytest.raises(StorageError, match="already exists"):
        storage.write_record("one", envelope)

    jsonl = storage.export(tmp_path / "records.jsonl", format="jsonl")
    assert json.loads(jsonl.read_text())["record"]["nested"] == {"a": [1, 2]}
    with pytest.raises(StorageError, match="already exists"):
        storage.export(jsonl, format="jsonl")
    exported = storage.export(tmp_path / "records.json", format="json")
    assert len(json.loads(exported.read_text())) == 1
    assert storage.export(jsonl, format="jsonl", overwrite=True) == jsonl
