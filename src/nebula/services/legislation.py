"""Congress.gov legislation operations."""

from collections.abc import Awaitable, Callable
from urllib.parse import parse_qs, urlsplit

from nebula.collection import (
    CollectionRequest,
    CollectionResult,
    CollectionRunner,
    PaginatedDiscovery,
    ResourceReference,
)
from nebula.collection.checkpoints import FileCheckpointStore
from nebula.collection.pagination import ResourcePage
from nebula.collection.runner import RetrievedResource
from nebula.congress_gov.client import CongressGovClient
from nebula.congress_gov.legislation_models import (
    CongressActionPage,
    CongressAmendmentPage,
    CongressBill,
    CongressBillListRequest,
)
from nebula.congress_gov.parsers import CongressBillParser
from nebula.core.exceptions import ParsingError
from nebula.storage.base import RecordStorage


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

    async def bill(
        self, congress: int, bill_type: str, bill_number: int
    ) -> CongressBill | None:
        """Retrieve one full bill record, or None when absent."""
        client = await self._congress()
        return await client.get_bill_model(congress, bill_type, bill_number)

    async def collect_bills(
        self, congress: int, bill_type: str
    ) -> list[CongressBill]:
        """Return successful typed bills in discovery order."""
        result = await self.collect_bills_result(congress, bill_type)
        return [
            record
            for record in result.records
            if isinstance(record, CongressBill)
        ]

    async def collect_bills_result(
        self,
        congress: int,
        bill_type: str,
        *,
        page_size: int = 250,
        storage: RecordStorage | None = None,
        checkpoint_store: FileCheckpointStore | None = None,
        resume: bool = False,
        overwrite: bool = False,
        preserve_raw: bool = False,
        retain_records: bool = True,
        progress: Callable[[int, int], None] | None = None,
    ) -> CollectionResult:
        """Discover and collect full bills with optional checkpointing."""
        options = CongressBillListRequest.model_validate(
            dict(congress=congress, bill_type=bill_type, limit=page_size)
        )
        client = await self._congress()
        base = urlsplit(client.BASE_URL)
        collection_path = (
            f"{base.path.rstrip('/')}/bill/"
            f"{options.congress}/{options.bill_type}"
        )

        def next_offset(next_url: str, current: int) -> str:
            parts = urlsplit(next_url)
            query = parse_qs(parts.query)
            offsets = query.get("offset", [])
            limits = query.get("limit", [])
            if (
                parts.scheme != "https"
                or parts.netloc != base.netloc
                or parts.path != collection_path
                or len(offsets) != 1
                or len(limits) != 1
                or not offsets[0].isdigit()
                or not limits[0].isdigit()
                or int(offsets[0]) <= current
                or int(limits[0]) != options.limit
            ):
                raise ParsingError("Invalid Congress.gov bill continuation")
            return offsets[0]

        async def fetch_page(cursor: str | None) -> ResourcePage:
            offset = int(cursor) if cursor is not None else 0
            page = await client.get_bill_page(
                options.congress,
                options.bill_type,
                offset=offset,
                limit=options.limit,
            )
            references: list[ResourceReference] = []
            for bill in page.bills:
                if (
                    bill.congress != options.congress
                    or bill.type.lower() != options.bill_type
                    or not bill.number.isdigit()
                    or int(bill.number) < 1
                ):
                    raise ParsingError("Invalid Congress.gov bill identity")
                number = int(bill.number)
                references.append(
                    ResourceReference(
                        resource_id=(
                            f"{options.congress}/{options.bill_type}/{number}"
                        ),
                        url=client.bill_url(
                            options.congress, options.bill_type, number
                        ),
                    )
                )
            continuation = (
                next_offset(page.pagination.next, offset)
                if page.pagination.next is not None
                else None
            )
            return ResourcePage(
                resources=references,
                next_cursor=continuation,
                complete=continuation is None,
            )

        request = CollectionRequest(
            source="congress_gov",
            collection_id=(
                f"congress-bills-{options.congress}-{options.bill_type}"
            ),
            parameters={
                "congress": options.congress,
                "bill_type": options.bill_type,
                "page_size": options.limit,
            },
            max_concurrency=client.config.max_concurrency,
            resume=resume,
            overwrite=overwrite,
            preserve_raw=preserve_raw,
            retain_records=retain_records,
        )

        async def fetch(
            ref: ResourceReference,
        ) -> RetrievedResource | None:
            number = int(ref.resource_id.rsplit("/", 1)[-1])
            return await client.fetch_bill_resource(
                options.congress, options.bill_type, number
            )

        runner = CollectionRunner(
            request,
            discovery=PaginatedDiscovery(fetch_page),
            fetch=fetch,
            parse=CongressBillParser().parse,
            storage=storage,
            checkpoint_store=checkpoint_store,
            progress=progress,
        )
        return await runner.run()
