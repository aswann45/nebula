"""Discovery strategies for explicit, HTML-index, and paginated sources."""

from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from pydantic import BaseModel, Field

from .models import ResourceReference


class DiscoveryStrategy(Protocol):
    """Discover stable resource references for a collection."""

    async def discover(self) -> list[ResourceReference]:
        """Return discoverable references in source order."""
        ...


class ExplicitDiscovery:
    """Return an explicit set of resource references in supplied order."""

    def __init__(self, references: Sequence[ResourceReference]) -> None:
        """Copy references so later caller changes cannot alter discovery."""
        self.references = tuple(references)

    async def discover(self) -> list[ResourceReference]:
        """Return the supplied references."""
        return list(self.references)


class HTMLIndexDiscovery:
    """Parse references from a retrieved HTML index document."""

    def __init__(
        self,
        fetch_index: Callable[[], Awaitable[bytes]],
        parse_index: Callable[[bytes], Sequence[ResourceReference]],
    ) -> None:
        """Bind independent retrieval and parsing operations."""
        self.fetch_index = fetch_index
        self.parse_index = parse_index

    async def discover(self) -> list[ResourceReference]:
        """Fetch one index and return its parsed resource references."""
        return list(self.parse_index(await self.fetch_index()))


class ResourcePage(BaseModel):
    """One API page with explicit continuation state."""

    resources: list[ResourceReference] = Field(default_factory=list)
    next_cursor: str | None = None
    complete: bool = False


class PaginatedDiscovery:
    """Follow explicit continuation cursors, including empty pages."""

    def __init__(
        self,
        fetch_page: Callable[[str | None], Awaitable[ResourcePage]],
    ) -> None:
        """Use a source-specific page fetcher."""
        self.fetch_page = fetch_page

    async def discover(self) -> list[ResourceReference]:
        """Collect pages until a source explicitly marks completion."""
        cursor: str | None = None
        seen: set[str | None] = set()
        references: list[ResourceReference] = []
        while True:
            if cursor in seen:
                raise ValueError("pagination cursor repeated")
            seen.add(cursor)
            page = await self.fetch_page(cursor)
            references.extend(page.resources)
            if page.complete:
                return references
            if page.next_cursor is None:
                raise ValueError("incomplete page has no continuation cursor")
            cursor = page.next_cursor
