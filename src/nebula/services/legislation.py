"""Congress.gov legislation operations."""

from collections.abc import Awaitable, Callable

from nebula.congress_gov.client import CongressGovClient
from nebula.congress_gov.legislation_models import (
    CongressActionPage,
    CongressAmendmentPage,
)


class LegislationService:
    """Retrieve bill and amendment activity from Congress.gov."""

    def __init__(
        self, congress: Callable[[], Awaitable[CongressGovClient]]
    ) -> None:
        """Use a lazily resolved Congress.gov client."""
        self._congress = congress

    async def bill_actions(
        self,
        congress: int,
        bill_type: str,
        bill_number: int,
        *,
        offset: int = 0,
        limit: int = 250,
    ) -> CongressActionPage:
        """Retrieve a page of actions for one bill."""
        client = await self._congress()
        return await client.get_bill_actions(
            congress, bill_type, bill_number, offset=offset, limit=limit
        )

    async def bill_amendments(
        self,
        congress: int,
        bill_type: str,
        bill_number: int,
        *,
        offset: int = 0,
        limit: int = 250,
    ) -> CongressAmendmentPage:
        """Retrieve a page of amendments to one bill."""
        client = await self._congress()
        return await client.get_bill_amendments(
            congress, bill_type, bill_number, offset=offset, limit=limit
        )

    async def amendment_actions(
        self,
        congress: int,
        amendment_type: str,
        amendment_number: int,
        *,
        offset: int = 0,
        limit: int = 250,
    ) -> CongressActionPage:
        """Retrieve a page of actions for one amendment."""
        client = await self._congress()
        return await client.get_amendment_actions(
            congress,
            amendment_type,
            amendment_number,
            offset=offset,
            limit=limit,
        )
