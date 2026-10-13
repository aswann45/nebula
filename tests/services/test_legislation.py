"""Offline Congress.gov legislation retrieval tests."""

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from nebula import Nebula
from nebula.cli.main import app
from nebula.congress_gov.client import CongressGovClient
from nebula.congress_gov.parsers import (
    CongressActionPageParser,
    CongressAmendmentPageParser,
)
from nebula.core.config import HTTPConfig
from nebula.core.exceptions import DataValidationError

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_legislation_parsers_validate_source_pages() -> None:
    """Parse action and amendment pages without an HTTP client."""
    actions = CongressActionPageParser().parse(
        (FIXTURES / "congress_actions.json").read_bytes()
    )
    amendments = CongressAmendmentPageParser().parse(
        (FIXTURES / "congress_amendments.json").read_bytes()
    )
    assert actions.actions[0].action_code == "E40000"
    assert actions.actions[0].model_extra["sourceSystem"]["code"] == 9
    assert actions.pagination.count == 74
    assert amendments.amendments[0].number == "4981"
    assert amendments.amendments[0].type == "SAMDT"
    with pytest.raises(DataValidationError):
        CongressActionPageParser().parse(b'{"actions": [{}]}')
    payload = json.loads((FIXTURES / "congress_actions.json").read_text())
    payload["pagination"]["next"] += "&api_key=private-key"
    safe_page = CongressActionPageParser().parse(json.dumps(payload).encode())
    assert "private-key" not in (safe_page.pagination.next or "")


def test_legislation_client_and_service_routes() -> None:
    """Route all three operations through the validated source client."""

    async def run() -> None:
        paths: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            paths.append(request.url.path)
            assert request.url.params["api_key"] == "test-key"
            assert request.url.params["format"] == "json"
            if request.url.path.endswith("/amendments"):
                content = (FIXTURES / "congress_amendments.json").read_bytes()
            else:
                content = (FIXTURES / "congress_actions.json").read_bytes()
            return httpx.Response(200, content=content)

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = CongressGovClient(
            API_KEY="test-key",
            http_client=http,
            config=HTTPConfig(max_retries=0),
        )
        async with Nebula(clients={"congress_gov": client}) as nebula:
            actions = await nebula.legislation.bill_actions(117, "HR", 3076)
            amendments = await nebula.legislation.bill_amendments(
                117, "hr", 3076
            )
            amendment_actions = await nebula.legislation.amendment_actions(
                117, "HAMDT", 173, offset=2, limit=5
            )
            assert actions.actions[0].text.startswith("Became")
            assert amendments.amendments[0].number == "4981"
            assert amendment_actions.actions[0].action_date.year == 2022
            with pytest.raises(ValidationError):
                await nebula.legislation.bill_actions(117, "bad", 1)
        assert paths == [
            "/v3/bill/117/hr/3076/actions",
            "/v3/bill/117/hr/3076/amendments",
            "/v3/amendment/117/hamdt/173/actions",
        ]
        await http.aclose()

    asyncio.run(run())


def test_legislation_cli_outputs_records(monkeypatch: Any) -> None:
    """Expose validated actions as machine-readable records."""
    from nebula.cli import common

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=(FIXTURES / "congress_actions.json").read_bytes()
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = CongressGovClient(API_KEY="test-key", http_client=http)
    monkeypatch.setattr(
        common,
        "create_nebula",
        lambda: Nebula(clients={"congress_gov": client}),
    )
    result = CliRunner().invoke(
        app,
        ["legislation", "bill-actions", "117", "hr", "3076"],
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["action_code"] == "E40000"
    asyncio.run(http.aclose())
