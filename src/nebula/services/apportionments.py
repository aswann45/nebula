"""OMB apportionment operations backed by the existing source client."""

from __future__ import annotations

import builtins
from collections.abc import Awaitable, Callable

from nebula.omb_apportionments.client import OMBApportionmentsClient
from nebula.omb_apportionments.models import (
    OMBApportionment,
    OMBApportionmentReference,
)
from nebula.omb_apportionments.parsers import OMBApportionmentParser


class ApportionmentService:
    """Discover and retrieve validated OMB apportionment records."""

    def __init__(
        self, omb: Callable[[], Awaitable[OMBApportionmentsClient]]
    ) -> None:
        """Use a lazily resolved OMB source client."""
        self._omb = omb

    async def list(self) -> list[OMBApportionmentReference]:
        """List the JSON resources currently linked by the OMB index."""
        client = await self._omb()
        return await client.list_apportionment_references()

    async def get(self, url: str) -> OMBApportionment | None:
        """Retrieve one OMB JSON resource, or None when it is missing."""
        client = await self._omb()
        return await client.get_apportionment_model(url)

    async def collect(
        self, fiscal_year: int | None = None
    ) -> builtins.list[OMBApportionment]:
        """Retrieve all listed records using the client's bounded workers.

        Returns
        -------
        list[OMBApportionment]
            Successfully retrieved records in index order. Missing files
            are omitted. Other source failures propagate to the caller.

        """
        client = await self._omb()
        responses = await client.get_apportionments_data()
        parser = OMBApportionmentParser()
        records = [
            parser.parse(response.text.encode())
            for response in responses
            if response is not None and response.text is not None
        ]
        return [
            record
            for record in records
            if fiscal_year is None or record.fiscal_year == fiscal_year
        ]
