"""Validated HTTP settings shared by source clients."""

from pydantic import BaseModel, ConfigDict, Field


class HTTPConfig(BaseModel):
    """Limits and retry policy for one source client's HTTP traffic."""

    model_config = ConfigDict(frozen=True)

    timeout: float = Field(default=30.0, gt=0)
    max_connections: int = Field(default=20, gt=0)
    max_concurrency: int = Field(default=5, gt=0)
    max_retries: int = Field(default=3, ge=0)
    backoff_factor: float = Field(default=0.5, ge=0)
