"""Lossy conversions from source records to minimal domain records.

Keep the source model when published fields beyond the shared identity are
needed. No network access occurs during these conversions.
"""

from typing import Literal

from nebula.congress_gov.member_model import Member
from nebula.github_congress.models import GitHubCommittee, GitHubMember
from nebula.house_clerk.models import HouseRollCall

from .committees import CommitteeRecord
from .members import MemberRecord
from .votes import VoteRecord


def _chamber(value: str) -> Literal["House", "Senate"] | None:
    text = value.lower()
    if "house" in text or text == "rep":
        return "House"
    if "senate" in text or text == "sen":
        return "Senate"
    return None


def normalize_congress_member(member: Member) -> MemberRecord:
    """Extract stable identity fields from a Congress.gov member."""
    return MemberRecord(
        source="congress_gov",
        bioguide_id=member.bioguide_id,
        name=member.direct_order_name,
        chamber=_chamber(member.terms[-1].chamber),
        state=member.state,
    )


def normalize_github_member(member: GitHubMember) -> MemberRecord:
    """Extract identity from the last published GitHub term."""
    latest = member.terms[-1]
    return MemberRecord(
        source="github_congress",
        bioguide_id=member.id.bioguide,
        name=member.name.official_full
        or f"{member.name.first} {member.name.last}",
        chamber=_chamber(latest.type),
        state=latest.state,
    )


def normalize_github_committee(
    committee: GitHubCommittee,
) -> CommitteeRecord:
    """Extract the shared committee identity from GitHub YAML."""
    return CommitteeRecord(
        source="github_congress",
        name=committee.name,
        chamber=_chamber(committee.type),
        source_id=committee.thomas_id,
    )


def normalize_house_roll_call(vote: HouseRollCall) -> VoteRecord:
    """Extract a House roll-call summary without member positions."""
    return VoteRecord(
        source="house_clerk",
        chamber="House",
        year=vote.year,
        roll_call_number=vote.roll_call_number,
        action_date=vote.action_date,
        result=vote.vote_result,
    )
