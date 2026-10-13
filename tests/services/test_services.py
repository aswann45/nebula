"""Domain services can be used independently of the facade."""

import asyncio
from pathlib import Path

import httpx

from nebula.github_congress.client import GitHubCongressClient
from nebula.services import CommitteeService, MemberService

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_member_and_committee_services_without_facade() -> None:
    """Delegate typed retrieval to a directly supplied source client."""

    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("legislators-current.yaml"):
                return httpx.Response(
                    200,
                    content=(FIXTURES / "github_members.yaml").read_bytes(),
                )
            return httpx.Response(
                200,
                content=(FIXTURES / "github_committees.yaml").read_bytes(),
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        github = GitHubCongressClient(http_client=http)

        async def resolve_github() -> GitHubCongressClient:
            return github

        async def unsupported() -> None:
            raise AssertionError("unexpected source request")

        members = MemberService(
            unsupported,
            resolve_github,
            unsupported,
            unsupported,  # type: ignore[arg-type]
        )
        committees = CommitteeService(resolve_github)
        assert len(await members.current()) == 2
        assert len(await members.list(chamber="senate")) == 2
        assert await members.list(chamber="house") == []
        assert len(await committees.list()) == 2
        await http.aclose()

    asyncio.run(run())
