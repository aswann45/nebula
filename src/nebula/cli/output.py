"""Shared serialization and file output for CLI commands."""

import csv
import io
import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from nebula.core.exceptions import StorageError


class OutputFormat(StrEnum):
    """Supported terminal and file representations."""

    TABLE = "table"
    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"


def normalize(value: Any) -> Any:
    """Convert Pydantic records and nested containers to JSON values."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    return value


def render(value: Any, output_format: OutputFormat) -> str:
    """Render public records without dropping nested fields."""
    data = normalize(value)
    if output_format == OutputFormat.JSON:
        return json.dumps(data, indent=2, default=str) + "\n"
    if output_format == OutputFormat.JSONL:
        items = data if isinstance(data, list) else [data]
        return "".join(
            json.dumps(item, separators=(",", ":"), default=str) + "\n"
            for item in items
        )
    if output_format == OutputFormat.CSV:
        return _render_csv(data)
    return _render_table(data)


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    if isinstance(data, list):
        return [{"value": item} for item in data]
    return [{"value": data}]


def _cell(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), default=str)
    return "" if value is None else str(value)


def _columns(rows: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(key for row in rows for key in row))


def _render_csv(data: Any) -> str:
    rows = _rows(data)
    if not rows:
        return ""
    columns = _columns(rows)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _cell(row.get(key)) for key in columns})
    return buffer.getvalue()


def _render_table(data: Any) -> str:
    rows = _rows(data)
    if not rows:
        return "No records found.\n"
    columns = _columns(rows)
    widths = {
        key: max(len(key), *(len(_cell(row.get(key))) for row in rows))
        for key in columns
    }
    header = "  ".join(key.ljust(widths[key]) for key in columns)
    divider = "  ".join("-" * widths[key] for key in columns)
    body = [
        "  ".join(_cell(row.get(key)).ljust(widths[key]) for key in columns)
        for row in rows
    ]
    return "\n".join([header, divider, *body]) + "\n"


def write_output(
    content: str,
    destination: str,
    *,
    output_format: OutputFormat,
    overwrite: bool,
    default_stem: str,
) -> Path:
    """Write output to a file or directory with explicit replacement."""
    path = Path(destination).expanduser()
    if destination.endswith("/") or path.is_dir():
        path = path / f"{default_stem}.{output_format.value}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if overwrite:
            path.write_text(content, encoding="utf-8")
        else:
            _write_new(path, content)
    except FileExistsError as exc:
        raise StorageError(
            f"{path} already exists; pass --overwrite to replace it"
        ) from exc
    except OSError as exc:
        raise StorageError(f"Could not write {path}: {exc.strerror}") from exc
    return path


def _write_new(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)
