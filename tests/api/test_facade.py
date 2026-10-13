"""Public facade, service, and source registry tests."""

import asyncio
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from nebula import (
    CongressGovClient,
    Nebula,
    OMBApportionmentsClient,
)
from nebula.core.config import HTTPConfig
from nebula.core.exceptions import DataValidationError
from nebula.github_congress.client import GitHubCongressClient
from nebula.house_clerk.client import HouseClerkClient
from nebula.schemas import BaseClient
from nebula.settings import Settings
from nebula.sources import SourceCapabilities, SourceRegistry

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_legacy_imports_and_root_exports() -> None:
    """Preserve client identity across root and direct source imports."""
    from nebula.congress_gov.client import CongressGovClient as DirectCongress
    from nebula.omb_apportionments.client import (
        OMBApportionmentsClient as DirectOMB,
    )

    assert CongressGovClient is DirectCongress
    assert OMBApportionmentsClient is DirectOMB


def test_registry_capabilities_and_configuration() -> None:
    """Register adapters explicitly and inspect their capabilities."""
    registry = SourceRegistry.with_defaults()
    assert set(registry.names()) == {
        "congress_gov",
        "github_congress",
        "house_clerk",
        "senate_clerk",
        "omb_apportionments",
    }
    assert registry.capabilities("omb_apportionments").apportionments
    assert registry.capabilities("house_clerk").votes
    assert not registry.capabilities("senate_clerk").votes
    assert isinstance(
        registry.create("github_congress", config=HTTPConfig(timeout=7)),
        GitHubCongressClient,
    )
    with pytest.raises(ValueError, match="already registered"):
        registry.register(
            "house_clerk", HouseClerkClient, SourceCapabilities(votes=True)
        )
    with pytest.raises(KeyError, match="unknown"):
        registry.capabilities("unknown")


def test_facade_services_use_injected_clients() -> None:
    """Route service calls through source clients and close owned pools."""

    async def run() -> None:
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.path)
            if request.url.path.endswith("legislators-current.yaml"):
                return httpx.Response(
                    200,
                    content=(FIXTURES / "github_members.yaml").read_bytes(),
                )
            if request.url.path.endswith("committees-current.yaml"):
                return httpx.Response(
                    200,
                    content=(FIXTURES / "github_committees.yaml").read_bytes(),
                )
            if request.url.path.endswith("roll001.xml"):
                return httpx.Response(
                    200, content=(FIXTURES / "house_roll.xml").read_bytes()
                )
            return httpx.Response(404)

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        github = GitHubCongressClient(http_client=http)
        house = HouseClerkClient(http_client=http)
        async with Nebula(
            clients={"github_congress": github, "house_clerk": house}
        ) as nebula:
            members = await nebula.members.current()
            senate_members = await nebula.members.list(chamber="senate")
            committees = await nebula.committees.current()
            vote = await nebula.votes.house(2026, 1)
            missing = await nebula.votes.house(2026, 2)
            assert members and committees
            assert senate_members and all(
                member.terms[-1].type == "sen" for member in senate_members
            )
            assert vote is not None
            assert missing is None
            assert await nebula.get_source("github_congress") is github
        assert not http.is_closed
        assert len(seen) == 5
        await http.aclose()

    asyncio.run(run())


def test_omb_service_discovery_and_retrieval() -> None:
    """Expose OMB JSON models through its domain service."""

    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/":
                return httpx.Response(
                    200, text='<a href="/record.json">record</a>'
                )
            if request.url.path == "/record.json":
                return httpx.Response(
                    200,
                    content=(FIXTURES / "omb_apportionment.json").read_bytes(),
                )
            return httpx.Response(404)

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = OMBApportionmentsClient(http_client=http)
        async with Nebula(clients={"omb_apportionments": client}) as nebula:
            references = await nebula.apportionments.list()
            assert len(references) == 1
            record = await nebula.apportionments.get(references[0].url)
            assert record is not None and record.file_id == 11547886
            assert await nebula.apportionments.get("/missing.json") is None
            collected = await nebula.apportionments.collect()
            assert [item.file_id for item in collected] == [11547886]
            assert await nebula.apportionments.collect(2026) == []
        await http.aclose()

    asyncio.run(run())


def test_facade_closes_owned_clients_after_failure() -> None:
    """Release a lazily created transport when context work raises."""

    async def run() -> None:
        client: BaseClient
        with pytest.raises(RuntimeError, match="failed"):
            async with Nebula() as nebula:
                client = await nebula.get_source("github_congress")
                assert isinstance(client, GitHubCongressClient)
                http = client._transport.client
                assert not http.is_closed
                raise RuntimeError("failed")
        assert http.is_closed

    asyncio.run(run())


def test_congress_settings_and_source_options() -> None:
    """Initialize Congress.gov only on demand with supplied credentials."""

    async def run() -> None:
        seen_keys: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_keys.append(request.url.params["api_key"])
            return httpx.Response(200, json={"bad": "record"})

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        settings = Settings(congress_gov_api_key=SecretStr("injected-secret"))
        async with Nebula(
            settings=settings,
            source_options={"congress_gov": {"http_client": http}},
        ) as nebula:
            with pytest.raises(DataValidationError):
                await nebula.members.get("B000490")
        assert seen_keys == ["injected-secret"]
        assert not http.is_closed
        await http.aclose()

    asyncio.run(run())
