"""Faithful typed records for the congressional legislators dataset."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class GitHubSourceModel(BaseModel):
    """Retain source-specific fields that have no canonical equivalent."""

    model_config = ConfigDict(extra="allow")


class GitHubMemberIdentifiers(GitHubSourceModel):
    """Published identifiers for one legislator."""

    bioguide: str = Field(min_length=1)


class GitHubMemberName(GitHubSourceModel):
    """Published name components for one legislator."""

    first: str
    last: str
    official_full: str | None = None


class GitHubMemberTerm(GitHubSourceModel):
    """A House or Senate term with normalized calendar dates."""

    type: str
    start: date
    end: date
    state: str
    district: int | None = None
    party: str | None = None


class GitHubMember(GitHubSourceModel):
    """One legislator with all published identifiers and terms."""

    id: GitHubMemberIdentifiers
    name: GitHubMemberName
    terms: list[GitHubMemberTerm] = Field(min_length=1)


class GitHubLeadershipRole(BaseModel):
    """Current leadership title in the legacy flattened member view."""

    role_name: str | None = None
    level: str = "leadership"


class GitHubCurrentMemberSummary(BaseModel):
    """Validate the flattened data returned by the legacy wrapper."""

    bioguide_id: str = Field(min_length=1)
    terms: list[GitHubMemberTerm] | None = None
    leadership_roles: list[GitHubLeadershipRole] | None = None


class GitHubSubcommittee(GitHubSourceModel):
    """A published subcommittee entry."""

    name: str
    thomas_id: str | None = None


class GitHubCommittee(GitHubSourceModel):
    """A published congressional committee and its subcommittees."""

    type: str
    name: str
    thomas_id: str | None = None
    subcommittees: list[GitHubSubcommittee] = Field(default_factory=list)


class GitHubHistoricalMembersRequest(BaseModel):
    """Validated lower year bound for historical retrieval."""

    year: int = Field(ge=1789)
