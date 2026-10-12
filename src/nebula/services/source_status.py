"""Configured availability and optional live source connectivity."""

import asyncio

import httpx
from pydantic import BaseModel, ConfigDict

from nebula.settings import Settings
from nebula.sources import SourceRegistry


class SourceStatus(BaseModel):
    """Configuration and optional probe result for one source."""

    model_config = ConfigDict(frozen=True)

    source: str
    configured: bool
    checked: bool = False
    reachable: bool | None = None
    detail: str | None = None


class SourceStatusService:
    """Inspect sources without making requests unless asked to probe."""

    def __init__(
        self,
        registry: SourceRegistry,
        settings: Settings,
        *,
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Store registry and credential state for status inspection."""
        self.registry = registry
        self.settings = settings
        self.timeout = timeout
        self._http_client = http_client

    async def status(self, *, check: bool = False) -> list[SourceStatus]:
        """Return configuration state and optional generic HTTP probes."""
        if not check:
            return [
                self._configured_status(name) for name in self.registry.names()
            ]
        if self._http_client is not None:
            return await self._check_all(self._http_client)
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            return await self._check_all(http)

    async def _check_all(self, http: httpx.AsyncClient) -> list[SourceStatus]:
        return await asyncio.gather(
            *(self._probe(http, name) for name in self.registry.names())
        )

    def _configured_status(self, name: str) -> SourceStatus:
        configured = name != "congress_gov" or bool(
            self.settings.congress_gov_api_key
        )
        return SourceStatus(source=name, configured=configured)

    async def _probe(self, http: httpx.AsyncClient, name: str) -> SourceStatus:
        status = self._configured_status(name)
        base_url = self.registry.client_type(name).BASE_URL
        if base_url is None:
            return status.model_copy(
                update={
                    "checked": True,
                    "reachable": False,
                    "detail": "No base URL configured",
                }
            )
        try:
            response = await http.get(base_url)
        except httpx.RequestError:
            return status.model_copy(
                update={
                    "checked": True,
                    "reachable": False,
                    "detail": "Network request failed",
                }
            )
        return status.model_copy(
            update={
                "checked": True,
                "reachable": response.status_code < 500,
                "detail": f"HTTP {response.status_code}",
            }
        )
