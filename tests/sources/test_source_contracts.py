"""Local fixture tests for source models and parsers."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from nebula.congress_gov.client import CongressGovClient
from nebula.congress_gov.parsers import CongressGovMemberParser
from nebula.congress_gov.schemas import CongressGovMemberResponse
from nebula.core.exceptions import DataValidationError, ParsingError
from nebula.github_congress.client import GitHubCongressClient
from nebula.github_congress.models import GitHubHistoricalMembersRequest
from nebula.github_congress.parsers import (
    GitHubCommitteeParser,
    GitHubHistoricalMemberParser,
    GitHubMemberParser,
)
from nebula.github_congress.schemas import GHCCurrentMemberResponse
from nebula.house_clerk.client import HouseClerkClient
from nebula.house_clerk.models import HouseRollCallRequest
from nebula.house_clerk.parsers import (
    HouseMemberParser,
    HouseRollCallParser,
)
from nebula.house_clerk.schemas import ClerkRollCallResponse
from nebula.models import SourceMetadata
from nebula.models.normalization import (
    normalize_github_committee,
    normalize_github_member,
    normalize_house_roll_call,
)
from nebula.omb_apportionments.client import OMBApportionmentsClient
from nebula.omb_apportionments.models import OMBApportionment
from nebula.omb_apportionments.parsers import (
    OMBApportionmentParser,
    OMBApportionmentReferenceParser,
)
from nebula.omb_apportionments.schemas import OMBSingleApportionmentResponse
from nebula.senate_clerk.parsers import SenateMemberParser
from nebula.senate_clerk.schemas import ClerkSenatorInfoResponse

FIXTURES = Path(__file__).parents[1] / "fixtures"


def fixture(name: str) -> bytes:
    """Read a source fixture without network access."""
    return (FIXTURES / name).read_bytes()


def test_omb_real_record_and_serialization() -> None:
    """Validate a real OMB record without losing codes or money."""
    record = OMBApportionmentParser().parse(fixture("omb_apportionment.json"))
    assert isinstance(record, OMBApportionment)
    assert record.file_id == 11547886
    assert record.approval_timestamp == datetime(
        2026, 8, 24, 10, 37, 48, 211751
    )
    assert record.schedule_data[0].cgac_account == "5066"
    assert record.schedule_data[0].cgac_agency == "096"
    assert record.schedule_data[0].begin_poa is None
    assert record.schedule_data[0].approved_amount == 0
    assert record.footnote_data[0].footnote_number == "A1"
    assert record.model_dump()["schedule_data"][0]["approved_amount"] == 0
    assert "schedule_data" in record.model_dump(mode="json")
    assert "schedule_data" in record.model_dump_json()


def test_omb_invalid_timestamp_and_fractional_amount() -> None:
    """Reject bad timestamps and fractional monetary amounts."""
    data = json.loads(fixture("omb_apportionment.json"))
    data["ApprovalTimestamp"] = "not-a-date"
    with pytest.raises(DataValidationError):
        OMBApportionmentParser().parse(json.dumps(data).encode())
    data["ApprovalTimestamp"] = None
    data["ScheduleData"][0]["ApprovedAmount"] = 0.5
    with pytest.raises(DataValidationError):
        OMBApportionmentParser().parse(json.dumps(data).encode())
    data["ScheduleData"][0]["ApprovedAmount"] = "42"
    record = OMBApportionmentParser().parse(json.dumps(data).encode())
    assert record.schedule_data[0].approved_amount == 42
    data["ScheduleData"][0]["ApprovedAmount"] = 42.0
    record = OMBApportionmentParser().parse(json.dumps(data).encode())
    assert record.schedule_data[0].approved_amount == 42


def test_omb_optional_fields_and_source_extras() -> None:
    """Allow absent optional metadata and preserve unknown source fields."""
    data = json.loads(fixture("omb_apportionment.json"))
    for key in ("Folder", "ApproverTitle", "FundsProvidedBy"):
        data.pop(key)
    data["PublishedExtra"] = "retained"
    data["ScheduleData"][0]["CgacAcct"] = "0007"
    data["ScheduleData"][0]["BeginPoa"] = "X"
    record = OMBApportionmentParser().parse(json.dumps(data).encode())
    assert record.folder is None
    assert record.schedule_data[0].cgac_account == "0007"
    assert record.schedule_data[0].begin_poa == "X"
    assert record.model_dump()["PublishedExtra"] == "retained"


def test_omb_discovery_filters_and_resolves() -> None:
    """Return typed references in source order from malformed HTML."""
    parser = OMBApportionmentReferenceParser(
        "https://apportionment-public.max.gov/"
    )
    references = parser.parse(
        b'<a href="/one.json">one<a href="/one.json">duplicate'
        b'<a href="https://evil.example/two.json">bad'
        b'<a href="/three.pdf">pdf'
        b'<a href="two.JSON">two'
    )
    assert [ref.file_name for ref in references] == ["one.json", "two.JSON"]
    assert references[0].url == (
        "https://apportionment-public.max.gov/one.json"
    )


def test_legacy_wrapper_serialization_does_not_parse() -> None:
    """Keep legacy properties while leaving dumps free of parsing."""
    for response in (
        OMBSingleApportionmentResponse(
            url="https://example.com/a.json", text="not JSON"
        ),
        CongressGovMemberResponse(url="https://example.com", text="bad"),
        GHCCurrentMemberResponse(url="https://example.com", text="bad"),
        ClerkRollCallResponse(
            url="https://example.com", text="bad", year=2025
        ),
        ClerkSenatorInfoResponse(url="https://example.com", text="bad"),
    ):
        assert "parsed_data" not in response.model_dump()
        assert "parsed_data" not in response.model_dump_json()
        assert response.source_metadata("test").source == "test"


def test_congressional_fixture_parsers() -> None:
    """Parse all available congressional source formats offline."""
    assert (
        len(
            HouseMemberParser()
            .parse(fixture("house_members.xml"))
            .data.members.member
        )
        == 2
    )
    assert (
        len(
            SenateMemberParser()
            .parse(fixture("senate_members.xml"))
            .senators.member
        )
        == 2
    )
    vote = HouseRollCallParser().parse(fixture("house_roll.xml"))
    assert vote.roll_call_number == 1
    assert len(vote.votes) == 3
    assert len(GitHubMemberParser().parse(fixture("github_members.yaml"))) == 2
    assert (
        len(
            GitHubHistoricalMemberParser().parse(
                fixture("github_historical.yaml")
            )
        )
        == 2
    )
    assert (
        GitHubHistoricalMemberParser()
        .parse(fixture("github_historical.yaml"))[0]
        .terms[0]
        .start.year
        == 1789
    )
    assert (
        len(GitHubCommitteeParser().parse(fixture("github_committees.yaml")))
        == 2
    )


def test_source_models_preserve_metadata() -> None:
    """Keep source extras and serialize dates and nested records."""
    members = GitHubMemberParser().parse(fixture("github_members.yaml"))
    assert members[0].terms[0].start.isoformat() == "1993-01-05"
    assert members[0].id.model_extra
    assert isinstance(members[0].model_dump(mode="json"), dict)
    assert normalize_github_member(members[0]).chamber == "Senate"

    committees = GitHubCommitteeParser().parse(
        fixture("github_committees.yaml")
    )
    assert normalize_github_committee(committees[0]).chamber == "House"

    vote = HouseRollCallParser().parse(fixture("house_roll.xml"))
    assert vote.source_metadata["vote-totals"]
    assert vote.votes[0].source_record["legislator"]
    assert vote.votes[0].normalized_position.value == "present"
    assert normalize_house_roll_call(vote).roll_call_number == 1
    assert "action_date" in vote.model_dump_json()
    assert (
        SourceMetadata(
            source="house_clerk",
            url="https://clerk.house.gov/evs/2025/roll001.xml",
            retrieved_at=datetime(2026, 10, 12),
        ).model_dump(mode="json")["source"]
        == "house_clerk"
    )


def test_congress_member_parser_validates_terms() -> None:
    """Parse a representative member response and reject empty terms."""
    payload = {
        "member": {
            "bioguideId": "B000490",
            "currentMember": True,
            "directOrderName": "Example Member",
            "firstName": "Example",
            "invertedOrderName": "Member, Example",
            "lastName": "Member",
            "partyHistory": [],
            "state": "NY",
            "terms": [
                {
                    "chamber": "House",
                    "congress": 119,
                    "memberType": "Representative",
                    "startYear": 2025,
                    "stateCode": "NY",
                    "stateName": "New York",
                }
            ],
            "updateDate": "2026-10-01",
        },
        "request": {
            "bioguideId": "B000490",
            "contentType": "application/json",
            "format": "json",
        },
    }
    parser = CongressGovMemberParser()
    assert parser.parse(json.dumps(payload).encode()).bioguide_id == "B000490"
    payload["member"]["terms"] = []
    with pytest.raises(DataValidationError):
        parser.parse(json.dumps(payload).encode())


def test_typed_client_methods_use_local_parsers() -> None:
    """Retrieve typed records through source clients with mocked HTTP."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path.endswith("roll001.xml"):
            return httpx.Response(200, content=fixture("house_roll.xml"))
        if request.url.path.endswith("legislators-current.yaml"):
            return httpx.Response(200, content=fixture("github_members.yaml"))
        if request.url.path.endswith("legislators-historical.yaml"):
            return httpx.Response(
                200, content=fixture("github_historical.yaml")
            )
        if request.url.path.endswith("omb.json"):
            return httpx.Response(
                200, content=fixture("omb_apportionment.json")
            )
        if request.url.path.endswith("/member/B000490"):
            return httpx.Response(200, json={"bad": "record"})
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http:
            house = HouseClerkClient(http_client=http)
            vote = await house.get_roll_call_vote_model(2025, 1)
            assert vote is not None and vote.roll_call_number == 1
            github = GitHubCongressClient(http_client=http)
            assert len(await github.get_current_members()) == 2
            assert len(await github.get_historical_members(1791)) == 1
            omb = OMBApportionmentsClient(http_client=http)
            record = await omb.get_apportionment_model(
                "https://apportionment-public.max.gov/omb.json"
            )
            assert record is not None and record.file_id == 11547886
            congress = CongressGovClient(API_KEY="test", http_client=http)
            with pytest.raises(DataValidationError):
                await congress.get_member_model("B000490")

    asyncio.run(run())
    assert "/evs/2025/roll001.xml" in seen


def test_congress_parser_rejects_invalid_json() -> None:
    """Expose a descriptive error for invalid Congress.gov JSON."""
    with pytest.raises(ParsingError):
        CongressGovMemberParser().parse(b"not JSON")


def test_public_request_models_and_discovery() -> None:
    """Validate typed parameters and return only OMB JSON references."""
    with pytest.raises(ValidationError):
        HouseRollCallRequest(year=2025, roll_call_number=0)
    with pytest.raises(ValidationError):
        GitHubHistoricalMembersRequest(year=1700)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text='<a href="/one.json">one</a>'
            '<a href="/one.json">duplicate</a>'
            '<a href="https://example.org/evil.json">bad</a>',
        )

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http:
            client = OMBApportionmentsClient(http_client=http)
            references = await client.list_apportionment_references()
            assert len(references) == 1
            assert references[0].file_name == "one.json"

    asyncio.run(run())
