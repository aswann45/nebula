"""House roll-call operations supported by the House Clerk."""

from collections.abc import Awaitable, Callable

from nebula.house_clerk.client import HouseClerkClient
from nebula.house_clerk.models import HouseRollCall


class VoteService:
    """Retrieve individual House votes and discover the current maximum."""

    def __init__(
        self, house: Callable[[], Awaitable[HouseClerkClient]]
    ) -> None:
        """Use a lazily resolved House Clerk client."""
        self._house = house

    async def house(
        self, year: int | str, roll_call_number: int | str
    ) -> HouseRollCall | None:
        """Retrieve one House vote, returning None for a missing roll call."""
        client = await self._house()
        return await client.get_roll_call_vote_model(year, roll_call_number)

    async def max_house_roll_call_number(self, year: int | str) -> int:
        """Read the maximum roll call listed for a House voting year."""
        client = await self._house()
        return await client.get_max_roll_call_number(year)
