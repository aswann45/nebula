"""Metadata kept separate from parsed source records."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceMetadata(BaseModel):
    """Provenance from one retrieval, without the parsed payload."""

    model_config = ConfigDict(frozen=True)

    source: str
    url: str
    retrieved_at: datetime
    last_modified: datetime | None = None
    content_type: str | None = None
