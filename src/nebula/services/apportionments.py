"""OMB apportionment operations backed by the existing source client."""

from __future__ import annotations

import builtins
from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from nebula.collection import (
    CollectionRequest,
    CollectionResult,
    CollectionRunner,
    HTMLIndexDiscovery,
    ResourceReference,
)
from nebula.collection.checkpoints import FileCheckpointStore
from nebula.core.transport import safe_url
from nebula.omb_apportionments.client import OMBApportionmentsClient
from nebula.omb_apportionments.models import (
    OMBApportionment,
    OMBApportionmentReference,
)
from nebula.omb_apportionments.parsers import (
    OMBApportionmentParser,
    OMBApportionmentReferenceParser,
)
from nebula.storage.base import RecordStorage


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
        """Return successful typed records from a bounded collection.

        Returns
        -------
        list[OMBApportionment]
            Successfully retrieved records in index order. Failed resources
            are reported by ``collect_result``.

        """
        result = await self.collect_result(fiscal_year)
        return [
            record
            for record in result.records
            if isinstance(record, OMBApportionment)
        ]

    async def collect_result(
        self,
        fiscal_year: int | None = None,
        *,
        storage: RecordStorage | None = None,
        checkpoint_store: FileCheckpointStore | None = None,
        resume: bool = False,
        overwrite: bool = False,
        preserve_raw: bool = False,
        retain_records: bool = True,
        progress: Callable[[int, int], None] | None = None,
    ) -> CollectionResult:
        """Collect OMB records with optional persistence and resumption."""
        client = await self._omb()
        reference_parser = OMBApportionmentReferenceParser(client.BASE_URL)

        def parse_index(content: bytes) -> list[ResourceReference]:
            return [
                ResourceReference(resource_id=safe_url(ref.url), url=ref.url)
                for ref in reference_parser.parse(content)
            ]

        def record_id(model: BaseModel, ref: ResourceReference) -> str:
            if isinstance(model, OMBApportionment):
                return str(model.file_id)
            return ref.resource_id

        request = CollectionRequest(
            source="omb_apportionments",
            collection_id=(
                f"omb-apportionments-{fiscal_year}"
                if fiscal_year is not None
                else "omb-apportionments-all"
            ),
            parameters={"fiscal_year": fiscal_year},
            max_concurrency=client.config.max_concurrency,
            resume=resume,
            overwrite=overwrite,
            preserve_raw=preserve_raw,
            retain_records=retain_records,
        )
        parser = OMBApportionmentParser()
        runner = CollectionRunner(
            request,
            discovery=HTMLIndexDiscovery(
                client.get_index_content, parse_index
            ),
            fetch=lambda ref: client.fetch_resource(ref.url),
            parse=parser.parse,
            storage=storage,
            checkpoint_store=checkpoint_store,
            record_id=record_id,
            include=lambda model: (
                isinstance(model, OMBApportionment)
                and (fiscal_year is None or model.fiscal_year == fiscal_year)
            ),
            progress=progress,
        )
        return await runner.run()
