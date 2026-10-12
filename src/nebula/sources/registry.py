"""Registry of supported source clients and their published capabilities."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from nebula.congress_gov.client import CongressGovClient
from nebula.github_congress.client import GitHubCongressClient
from nebula.house_clerk.client import HouseClerkClient
from nebula.omb_apportionments.client import OMBApportionmentsClient
from nebula.schemas import BaseClient
from nebula.senate_clerk.client import SenateClerkClient


class SourceCapabilities(BaseModel):
    """Domains and bulk retrieval supported by a source adapter."""

    model_config = ConfigDict(frozen=True)

    members: bool = False
    committees: bool = False
    legislation: bool = False
    votes: bool = False
    apportionments: bool = False
    bulk_collection: bool = False


class SourceRegistry:
    """Register source clients by stable name with explicit capabilities."""

    def __init__(self) -> None:
        """Create an initially empty registry."""
        self._entries: dict[
            str, tuple[type[BaseClient], SourceCapabilities]
        ] = {}

    def register(
        self,
        name: str,
        client_type: type[BaseClient],
        capabilities: SourceCapabilities,
    ) -> None:
        """Register a client type once under a nonempty source name."""
        if not name:
            raise ValueError("source name must not be empty")
        if name in self._entries:
            raise ValueError(f"source {name!r} is already registered")
        self._entries[name] = (client_type, capabilities)

    def names(self) -> tuple[str, ...]:
        """Return registered source names in registration order."""
        return tuple(self._entries)

    def capabilities(self, name: str) -> SourceCapabilities:
        """Return the declared capabilities of a registered source."""
        return self._entry(name)[1]

    def client_type(self, name: str) -> type[BaseClient]:
        """Return a registered source's client class."""
        return self._entry(name)[0]

    def create(self, name: str, **kwargs: Any) -> BaseClient:
        """Initialize a registered client with source-specific options."""
        return self.client_type(name)(**kwargs)

    def _entry(self, name: str) -> tuple[type[BaseClient], SourceCapabilities]:
        try:
            return self._entries[name]
        except KeyError:
            raise KeyError(f"unknown source {name!r}") from None

    @classmethod
    def with_defaults(cls) -> "SourceRegistry":
        """Register all five built-in source adapters."""
        registry = cls()
        registry.register(
            "congress_gov",
            CongressGovClient,
            SourceCapabilities(members=True, bulk_collection=True),
        )
        registry.register(
            "house_clerk",
            HouseClerkClient,
            SourceCapabilities(members=True, votes=True, bulk_collection=True),
        )
        registry.register(
            "senate_clerk",
            SenateClerkClient,
            SourceCapabilities(members=True),
        )
        registry.register(
            "github_congress",
            GitHubCongressClient,
            SourceCapabilities(
                members=True, committees=True, bulk_collection=True
            ),
        )
        registry.register(
            "omb_apportionments",
            OMBApportionmentsClient,
            SourceCapabilities(apportionments=True, bulk_collection=True),
        )
        return registry
