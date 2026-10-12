"""Member operations across congressional sources."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Literal

from nebula.congress_gov.client import CongressGovClient
from nebula.congress_gov.member_model import Member
from nebula.github_congress.client import GitHubCongressClient
from nebula.github_congress.models import GitHubMember
from nebula.house_clerk.client import HouseClerkClient
from nebula.house_clerk.member_model import ClerkData as HouseClerkData
from nebula.senate_clerk.client import SenateClerkClient
from nebula.senate_clerk.member_model import ClerkData as SenateClerkData


class MemberService:
    """Retrieve member data through its source-specific typed contracts."""

    def __init__(
        self,
        congress: Callable[[], Awaitable[CongressGovClient]],
        github: Callable[[], Awaitable[GitHubCongressClient]],
        house: Callable[[], Awaitable[HouseClerkClient]],
        senate: Callable[[], Awaitable[SenateClerkClient]],
    ) -> None:
        """Use lazily resolved clients so credentials are needed on demand."""
        self._congress = congress
        self._github = github
        self._house = house
        self._senate = senate

    async def get(self, bioguide_id: str) -> Member:
        """Retrieve a member by Bioguide ID from Congress.gov."""
        client = await self._congress()
        return await client.get_member_model(bioguide_id)

    async def get_many(
        self, bioguide_ids: Sequence[str]
    ) -> Mapping[str, Member]:
        """Retrieve members through Congress.gov's bounded bulk method."""
        client = await self._congress()
        return await client.get_member_data(bioguide_ids)

    async def current(self) -> list[GitHubMember]:
        """Retrieve current legislators from the GitHub dataset."""
        client = await self._github()
        return await client.get_current_members()

    async def historical(self, year: int | str) -> list[GitHubMember]:
        """Retrieve historical legislators active through a minimum year."""
        client = await self._github()
        return await client.get_historical_members(year)

    async def house_current(self) -> HouseClerkData:
        """Retrieve the House Clerk's current member roster."""
        client = await self._house()
        return await client.get_current_member_model()

    async def senate_current(self) -> SenateClerkData:
        """Retrieve the Senate Clerk's current member roster."""
        client = await self._senate()
        return await client.get_current_member_model()

    async def list(
        self, *, chamber: Literal["house", "senate"] | None = None
    ) -> list[GitHubMember]:
        """List current legislators, optionally filtering by chamber."""
        members = await self.current()
        if chamber is None:
            return members
        term_type = {"house": "rep", "senate": "sen"}[chamber]
        return [
            member for member in members if member.terms[-1].type == term_type
        ]
