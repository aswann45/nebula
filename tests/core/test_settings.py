"""Tests for environment-backed source credentials."""

from pathlib import Path

import pytest
from pydantic import SecretStr

from nebula.congress_gov.client import CongressGovClient
from nebula.core.exceptions import ConfigurationError
from nebula.settings import Settings


def test_dotenv_loads_and_environment_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Read a local dotenv file and prefer an environment override."""
    directory = tmp_path
    (directory / ".env").write_text("CONGRESS_GOV_API_KEY=from-file\n")
    monkeypatch.chdir(directory)
    monkeypatch.delenv("CONGRESS_GOV_API_KEY", raising=False)
    assert Settings().congress_gov_api_key == SecretStr("from-file")
    monkeypatch.setenv("CONGRESS_GOV_API_KEY", "from-env")
    assert Settings().congress_gov_api_key == SecretStr("from-env")
    assert "from-env" not in repr(Settings())


def test_congress_client_reads_current_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Load credentials at construction and retain explicit overrides."""
    directory = tmp_path
    monkeypatch.chdir(directory)
    monkeypatch.delenv("CONGRESS_GOV_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="not configured"):
        CongressGovClient()
    (directory / ".env").write_text("CONGRESS_GOV_API_KEY=from-file\n")
    assert CongressGovClient().API_KEY == "from-file"
    assert CongressGovClient(API_KEY="explicit").API_KEY == "explicit"
    injected = Settings(congress_gov_api_key=SecretStr("injected"))
    assert CongressGovClient(source_settings=injected).API_KEY == "injected"
