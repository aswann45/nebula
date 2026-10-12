"""Offline command tests for the Typer interface."""

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
from typer.testing import CliRunner

from nebula import Nebula
from nebula.cli.main import app
from nebula.core.config import HTTPConfig
from nebula.core.exceptions import SourceUnavailableError
from nebula.omb_apportionments.client import OMBApportionmentsClient


def test_help_version_and_source_inspection() -> None:
    """Expose registered commands without making network requests."""
    runner = CliRunner()
    assert runner.invoke(app, ["--help"]).exit_code == 0
    assert "0.1.0" in runner.invoke(app, ["--version"]).output
    listed = runner.invoke(app, ["sources", "list", "--format", "json"])
    assert listed.exit_code == 0
    assert len(json.loads(listed.stdout)) == 5
    status = runner.invoke(app, ["sources", "status", "--format", "json"])
    assert status.exit_code == 0
    assert "configured" in status.stdout


def test_config_show_redacts_and_validates() -> None:
    """Never reveal an API key through configuration commands."""
    runner = CliRunner()
    shown = runner.invoke(
        app,
        ["config", "show", "--format", "json"],
        env={"CONGRESS_GOV_API_KEY": "cli-test-secret"},
    )
    assert shown.exit_code == 0
    assert "cli-test-secret" not in shown.output
    assert runner.invoke(app, ["config", "validate"]).exit_code == 0


def test_member_output_and_file_overwrite(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Keep JSON machine-readable and require explicit file overwrite."""
    from nebula.cli import common

    class Members:
        async def list(self, *, chamber: str | None = None) -> list[dict]:
            return [{"name": "Ada", "terms": [{"chamber": chamber}]}]

    class FakeNebula:
        members = Members()

        async def __aenter__(self) -> "FakeNebula":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(common, "create_nebula", FakeNebula)
    runner = CliRunner()
    path = tmp_path / "members.json"
    args = [
        "members",
        "list",
        "--chamber",
        "house",
        "--format",
        "json",
        "--output",
        str(path),
    ]
    assert runner.invoke(app, args).exit_code == 0
    assert json.loads(path.read_text())[0]["name"] == "Ada"
    assert runner.invoke(app, args).exit_code != 0
    assert runner.invoke(app, [*args, "--overwrite"]).exit_code == 0


def test_csv_preserves_nested_values(monkeypatch: Any) -> None:
    """Serialize nested values into CSV cells instead of dropping them."""
    from nebula.cli import common

    class Committees:
        async def current(self) -> list[dict]:
            return [{"name": "Rules", "members": ["A", "B"]}]

    class FakeNebula:
        committees = Committees()

        async def __aenter__(self) -> "FakeNebula":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(common, "create_nebula", FakeNebula)
    result = CliRunner().invoke(app, ["committees", "list", "--format", "csv"])
    assert result.exit_code == 0
    assert '[""A"",""B""]' in result.stdout


def test_omb_collect_directory_output(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Write fiscal-year JSONL to a deterministic file name."""
    from nebula.cli import common

    fixture = Path(__file__).parents[1] / "fixtures" / "omb_apportionment.json"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(200, text='<a href="/one.json">one</a>')
        return httpx.Response(200, content=fixture.read_bytes())

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OMBApportionmentsClient(
        http_client=http, config=HTTPConfig(max_retries=0)
    )
    monkeypatch.setattr(
        common,
        "create_nebula",
        lambda: Nebula(clients={"omb_apportionments": client}),
    )
    destination = str(tmp_path / "omb") + "/"
    result = CliRunner().invoke(
        app,
        [
            "apportionments",
            "collect",
            "--fiscal-year",
            "2027",
            "--output",
            destination,
        ],
    )
    assert result.exit_code == 0
    output = tmp_path / "omb" / "omb-apportionments-2027.jsonl"
    assert json.loads(output.read_text())["record"]["file_id"] == 11547886
    asyncio.run(http.aclose())


def test_omb_cli_partial_failure_and_resume(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Keep a partial JSONL export and finish it on --resume."""
    from nebula.cli import common

    fixture = Path(__file__).parents[1] / "fixtures" / "omb_apportionment.json"
    missing = True
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(
                200,
                text='<a href="/one.json">one</a><a href="/two.json">two</a>',
            )
        paths.append(request.url.path)
        if request.url.path == "/two.json" and missing:
            return httpx.Response(404)
        return httpx.Response(200, content=fixture.read_bytes())

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OMBApportionmentsClient(
        http_client=http, config=HTTPConfig(max_retries=0)
    )
    monkeypatch.setattr(
        common,
        "create_nebula",
        lambda: Nebula(clients={"omb_apportionments": client}),
    )
    directory = str(tmp_path / "omb") + "/"
    args = [
        "apportionments",
        "collect",
        "--fiscal-year",
        "2027",
        "--output",
        directory,
    ]
    first = CliRunner().invoke(app, args)
    assert first.exit_code == 6
    output = tmp_path / "omb" / "omb-apportionments-2027.jsonl"
    assert len(output.read_text().splitlines()) == 1
    missing = False
    second = CliRunner().invoke(app, [*args, "--resume"])
    assert second.exit_code == 0
    assert len(output.read_text().splitlines()) == 2
    assert paths.count("/one.json") == 1
    asyncio.run(http.aclose())


def test_argument_and_network_exit_codes(monkeypatch: Any) -> None:
    """Return distinct codes for invalid arguments and source failures."""
    from nebula.cli import common

    class Members:
        async def list(self, *, chamber: str | None = None) -> list:
            raise SourceUnavailableError("source unavailable")

    class FakeNebula:
        members = Members()

        async def __aenter__(self) -> "FakeNebula":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(common, "create_nebula", FakeNebula)
    runner = CliRunner()
    assert (
        runner.invoke(
            app, ["members", "historical", "--year", "1700"]
        ).exit_code
        == 2
    )
    failed = runner.invoke(app, ["members", "list", "--format", "json"])
    assert failed.exit_code == 4
    assert "source unavailable" in failed.output
