"""Committee operations supported by the GitHub dataset."""

from collections.abc import Awaitable, Callable

from nebula.github_congress.client import GitHubCongressClient
from nebula.github_congress.models import GitHubCommittee


class CommitteeService:
    """Retrieve validated source committee records."""

    def __init__(
        self, github: Callable[[], Awaitable[GitHubCongressClient]]
    ) -> None:
        """Use a lazily resolved GitHub source client."""
        self._github = github

    async def current(self) -> list[GitHubCommittee]:
        """Retrieve the published current congressional committees."""
        client = await self._github()
        return await client.get_current_committees()

    async def list(self) -> list[GitHubCommittee]:
        """List the published current congressional committees."""
        return await self.current()
