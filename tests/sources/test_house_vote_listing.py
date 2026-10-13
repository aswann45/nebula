"""Offline checks for the Clerk's paginated vote listing."""

import pytest

from nebula.core.exceptions import ParsingError
from nebula.house_clerk.parsers import HouseVoteListingParser


def test_listing_parser_reads_rolls_and_result_count() -> None:
    """Read IDs and continue using the published result count."""
    html = b"""
    <div class="pagination_info">1 - 2 of 3 Results</div>
    <a href="/help">2026</a>
    <a aria-label="Roll number, 3" href="/Votes/20263?Page=2">3</a>
    <a aria-label="Roll number, 1" href="/Votes/20261">1</a>
    """
    assert HouseVoteListingParser().parse(html, 2026) == ([3, 1], True)


def test_listing_parser_crosses_pagination_window() -> None:
    """Continue when the Clerk omits Next at a page-window boundary."""
    html = b"""
    <div class="pagination_info">301 - 310 of 314 Results</div>
    <a aria-label="Roll number, 5" href="/Votes/20265">5</a>
    """
    assert HouseVoteListingParser().parse(html, 2026) == ([5], True)


def test_listing_parser_rejects_wrong_year() -> None:
    """A wrong-year listing must not silently become an empty collection."""
    html = b'<a aria-label="Roll number, 3" href="/Votes/20253">3</a>'
    with pytest.raises(ParsingError):
        HouseVoteListingParser().parse(html, 2026)


def test_listing_parser_accepts_empty_result() -> None:
    """An explicit empty result means the year has no published votes."""
    html = b'<p class="roll-call-description">No Votes Found</p>'
    assert HouseVoteListingParser().parse(html, 2026) == ([], False)
