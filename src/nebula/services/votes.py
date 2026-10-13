"""House roll-call operations supported by the House Clerk."""

from collections.abc import Awaitable, Callable

from nebula.collection import (
    CollectionRequest,
    CollectionResult,
    CollectionRunner,
    ExplicitDiscovery,
    ResourceReference,
)
from nebula.collection.checkpoints import FileCheckpointStore
from nebula.house_clerk.client import HouseClerkClient
from nebula.house_clerk.models import HouseRollCall
from nebula.house_clerk.parsers import HouseRollCallParser
from nebula.storage.base import RecordStorage


class VoteService:
    """Retrieve individual House votes and published voting years."""

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

    async def house_year(self, year: int | str) -> list[HouseRollCall]:
        """Return successful House votes from a bounded collection."""
        result = await self.house_year_result(year)
        return [
            record
            for record in result.records
            if isinstance(record, HouseRollCall)
        ]

    async def house_year_result(
        self,
        year: int | str,
        *,
        storage: RecordStorage | None = None,
        checkpoint_store: FileCheckpointStore | None = None,
        resume: bool = False,
        overwrite: bool = False,
        preserve_raw: bool = False,
        retain_records: bool = True,
        progress: Callable[[int, int], None] | None = None,
    ) -> CollectionResult:
        """Collect listed House votes with optional persistence and resume."""
        client = await self._house()
        voting_year = int(year)
        references = [
            ResourceReference(
                resource_id=f"{voting_year}/{number}",
                url=client.roll_call_url(voting_year, number),
            )
            for number in await client.list_roll_call_numbers(voting_year)
        ]
        request = CollectionRequest(
            source="house_clerk",
            collection_id=f"house-votes-{voting_year}",
            parameters={"year": voting_year},
            max_concurrency=client.config.max_concurrency,
            resume=resume,
            overwrite=overwrite,
            preserve_raw=preserve_raw,
            retain_records=retain_records,
        )
        runner = CollectionRunner(
            request,
            discovery=ExplicitDiscovery(references),
            fetch=lambda ref: client.fetch_roll_call_resource(
                voting_year, int(ref.resource_id.rsplit("/", 1)[-1])
            ),
            parse=HouseRollCallParser().parse,
            storage=storage,
            checkpoint_store=checkpoint_store,
            progress=progress,
        )
        return await runner.run()
