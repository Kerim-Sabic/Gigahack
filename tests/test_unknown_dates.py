import pytest

from services.api.dates import resolve


@pytest.mark.parametrize("raw", ["tomorrow", "mâine", "завтра", "today", "9 June", "9 июня", "9 iunie", "03/04"])
def test_missing_meeting_date_never_borrows_current_year_or_day(raw):
    assert resolve(raw, "") is None
    assert resolve(raw, None) is None


def test_explicit_full_date_can_resolve_without_meeting_date():
    assert resolve("2027-06-09", "") == "2027-06-09"
    assert resolve("9 июня 2027", "") == "2027-06-09"
