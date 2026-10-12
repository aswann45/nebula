"""Unified, lifecycle-aware access to Nebula's source-backed domains."""

import asyncio
from collections.abc import Mapping
from contextlib import AsyncExitStack
from typing import Any, Self, cast

from nebula.congress_gov.client import CongressGovClient
from nebula.core.config import HTTPConfig
from nebula.core.exceptions import ConfigurationError
from nebula.github_congress.client import GitHubCongressClient
from nebula.house_clerk.client import HouseClerkClient
from nebula.omb_apportionments.client import OMBApportionmentsClient
from nebula.schemas import BaseClient
from nebula.senate_clerk.client import SenateClerkClient
from nebula.services import (
    ApportionmentService,
    CommitteeService,
    LegislationService,
    MemberService,
    VoteService,
)
from nebula.settings import Settings
from nebula.sources import SourceRegistry


class Nebula:
    """Coordinate source lifecycles and expose supported domain services.

    Clients are constructed only when a service needs them. Congress.gov
    credentials are therefore optional until member lookup is requested.

    Parameters
    ----------
    config : HTTPConfig, optional
        Default transport configuration for created source clients.
    settings : Settings, optional
        Validated source credentials; environment settings are used when
        omitted.
    registry : SourceRegistry, optional
        Explicit source registrations. Defaults to the five built-in sources.
    clients : Mapping[str, BaseClient], optional
        Preconstructed source clients, useful for custom HTTP transports.
    source_options : Mapping[str, Mapping[str, Any]], optional
        Source-specific constructor options for clients created by Nebula.

    """

    def __init__(
        self,
        *,
        config: HTTPConfig | None = None,
        settings: Settings | None = None,
        registry: SourceRegistry | None = None,
        clients: Mapping[str, BaseClient] | None = None,
        source_options: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        """Validate injected clients and prepare lazy domain services."""
        self.config = config or HTTPConfig()
        self.settings = settings
        self.sources = registry or SourceRegistry.with_defaults()
        self._clients = dict(clients or {})
        for name, client in self._clients.items():
            if not isinstance(client, self.sources.client_type(name)):
                raise ConfigurationError(
                    f"Injected client has the wrong type for {name}"
                )
        self._source_options = {
            name: dict(options)
            for name, options in (source_options or {}).items()
        }
        for name in self._source_options:
            self.sources.client_type(name)
        self._lock = asyncio.Lock()
        self._stack: AsyncExitStack | None = None
        self._entered_names: set[str] = set()
        self.members = MemberService(
            self._congress, self._github, self._house, self._senate
        )
        self.committees = CommitteeService(self._github)
        self.legislation = LegislationService()
        self.votes = VoteService(self._house)
        self.apportionments = ApportionmentService(self._omb)

    async def __aenter__(self) -> Self:
        """Enter existing clients and reuse their pools during this scope."""
        if self._stack is not None:
            raise ConfigurationError("Nebula is already in an async context")
        self._stack = AsyncExitStack()
        try:
            for name, client in self._clients.items():
                await self._stack.enter_async_context(client)
                self._entered_names.add(name)
        except BaseException:
            await self.aclose()
            raise
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close owned client pools even when the operation fails."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close all entered source clients."""
        stack = self._stack
        self._stack = None
        self._entered_names.clear()
        if stack is not None:
            await stack.aclose()

    async def get_source(self, name: str) -> BaseClient:
        """Get a registered source client, creating it on first use."""
        async with self._lock:
            client = self._clients.get(name)
            if client is None:
                options = dict(self._source_options.get(name, {}))
                options.setdefault("config", self.config)
                if name == "congress_gov" and self.settings is not None:
                    options.setdefault("source_settings", self.settings)
                client = self.sources.create(name, **options)
                self._clients[name] = client
            if self._stack is not None and name not in self._entered_names:
                await self._stack.enter_async_context(client)
                self._entered_names.add(name)
            return client

    async def _congress(self) -> CongressGovClient:
        return cast(CongressGovClient, await self.get_source("congress_gov"))

    async def _github(self) -> GitHubCongressClient:
        return cast(
            GitHubCongressClient, await self.get_source("github_congress")
        )

    async def _house(self) -> HouseClerkClient:
        return cast(HouseClerkClient, await self.get_source("house_clerk"))

    async def _senate(self) -> SenateClerkClient:
        return cast(SenateClerkClient, await self.get_source("senate_clerk"))

    async def _omb(self) -> OMBApportionmentsClient:
        return cast(
            OMBApportionmentsClient,
            await self.get_source("omb_apportionments"),
        )
