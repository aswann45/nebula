"""Source status distinguishes local configuration and live probes."""

import asyncio

import httpx
from pydantic import SecretStr

from nebula.services.source_status import SourceStatusService
from nebula.settings import Settings
from nebula.sources import SourceRegistry


def test_live_checks_are_opt_in() -> None:
    """Avoid all requests until an explicit check is requested."""

    async def run() -> None:
        requests = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal requests
            requests += 1
            return httpx.Response(200)

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = SourceStatusService(
            SourceRegistry.with_defaults(),
            Settings(congress_gov_api_key=SecretStr("test")),
            http_client=http,
        )
        configured = await service.status()
        assert requests == 0
        assert all(item.configured and not item.checked for item in configured)
        checked = await service.status(check=True)
        assert requests == 5
        assert all(item.reachable and item.checked for item in checked)
        assert not http.is_closed
        await http.aclose()

    asyncio.run(run())
