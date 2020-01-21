import datetime

import pytest
import pytz

from courses.constants import SemesterTypes
from courses.utils import get_term_index, get_term_by_index, \
    get_current_term_pair, get_boundaries, TermPair, TermIndexError


def test_get_term_index(settings):
    established = settings.FOUNDATION_YEAR = 2011
    cnt = len(SemesterTypes.choices)
    with pytest.raises(ValueError) as e:
        get_term_index(established - 1, SemesterTypes.SPRING)
    assert "target year < FOUNDATION_YEAR" in str(e.value)
    with pytest.raises(ValueError) as e:
        get_term_index(established, "sprEng")
    assert "unknown term type" in str(e.value)
    assert get_term_index(established, SemesterTypes.SPRING) == 0
    assert get_term_index(established, SemesterTypes.SUMMER) == 1
    assert get_term_index(established, SemesterTypes.AUTUMN) == 2
    assert get_term_index(established + 1, SemesterTypes.SPRING) == cnt
    assert get_term_index(established + 1, SemesterTypes.SUMMER) == cnt + 1
    assert get_term_index(established + 7, SemesterTypes.SPRING) == cnt * 7


def test_get_boundaries():
    """Compare calculated values with wall calendar"""
    d1, d2 = get_boundaries(2016, 2)
    assert d1 == datetime.date(2016, 2, 1)
    assert d2 == datetime.date(2016, 3, 6)
    d1, d2 = get_boundaries(2019, 1)
    assert d1 == datetime.date(2018, 12, 31)
    assert d2 == datetime.date(2019, 2, 3)
    d1, d2 = get_boundaries(2019, 9)
    assert d1 == datetime.date(2019, 8, 26)
    assert d2 == datetime.date(2019, 10, 6)


def test_get_term_by_index(settings):
    established = settings.FOUNDATION_YEAR = 2011
    with pytest.raises(TermIndexError) as excinfo:
        get_term_by_index(-1)
    term_pair = get_term_by_index(0)
    assert isinstance(term_pair.year, int)
    assert term_pair.year == established
    # Check terms ordering
    assert term_pair.type == SemesterTypes.SPRING
    assert get_term_by_index(1).type == SemesterTypes.SUMMER
    assert get_term_by_index(2).type == SemesterTypes.AUTUMN
    term_pair = get_term_by_index(len(SemesterTypes.choices))
    assert term_pair.year == established + 1
    assert term_pair.type == SemesterTypes.SPRING
    term_pair = get_term_by_index(2 * len(SemesterTypes.choices))
    assert term_pair.year == established + 2
    assert term_pair.type == SemesterTypes.SPRING


def test_term_tuple_academic_year():
    assert TermPair(2011, SemesterTypes.AUTUMN).academic_year == 2011
    assert TermPair(2012, SemesterTypes.SPRING).academic_year == 2011
    assert TermPair(2012, SemesterTypes.AUTUMN).academic_year == 2012
    assert TermPair(2013, SemesterTypes.SUMMER).academic_year == 2012


@pytest.mark.django_db
def test_get_current_semester_pair(settings, mocker):
    settings.TIME_ZONE = 'Etc/UTC'
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    msk_tz = pytz.timezone("Europe/Moscow")
    mocked_timezone.return_value = msk_tz.localize(
        datetime.datetime(2014, 4, 1, 12, 0))
    assert TermPair(2014, SemesterTypes.SPRING) == get_current_term_pair(msk_tz)
    mocked_timezone.return_value = msk_tz.localize(datetime.datetime(2015, 11, 1, 12, 0))
    assert TermPair(2015, SemesterTypes.AUTUMN) == get_current_term_pair(msk_tz)
