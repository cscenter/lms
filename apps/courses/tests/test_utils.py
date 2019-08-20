import datetime

import pytest
import pytz

from courses.constants import SemesterTypes
from courses.utils import get_term_index, get_term_by_index, \
    first_term_in_academic_year, get_current_term_pair, \
    TERMS_INDEX_START
from core.settings.base import FOUNDATION_YEAR


def test_get_term_index():
    cnt = len(SemesterTypes.choices)
    with pytest.raises(ValueError) as e:
        get_term_index(FOUNDATION_YEAR - 1, SemesterTypes.SPRING)
    assert "target year < FOUNDATION_YEAR" in str(e.value)
    with pytest.raises(ValueError) as e:
        get_term_index(FOUNDATION_YEAR, "sprEng")
    assert "unknown term type" in str(e.value)
    assert get_term_index(FOUNDATION_YEAR,
                          SemesterTypes.SPRING) == TERMS_INDEX_START
    assert get_term_index(FOUNDATION_YEAR,
                          SemesterTypes.SUMMER) == TERMS_INDEX_START + 1
    assert get_term_index(FOUNDATION_YEAR,
                          SemesterTypes.AUTUMN) == TERMS_INDEX_START + 2
    assert get_term_index(FOUNDATION_YEAR + 1,
                          SemesterTypes.SPRING) == TERMS_INDEX_START + cnt
    assert get_term_index(FOUNDATION_YEAR + 1,
                          SemesterTypes.SUMMER) == TERMS_INDEX_START + cnt + 1
    assert get_term_index(FOUNDATION_YEAR + 7,
                          SemesterTypes.SPRING) == TERMS_INDEX_START + cnt * 7


def test_get_term_by_index():
    with pytest.raises(AssertionError) as excinfo:
        get_term_by_index(TERMS_INDEX_START - 1)
    year, term = get_term_by_index(TERMS_INDEX_START)
    assert isinstance(year, int)
    assert year == FOUNDATION_YEAR
    # Check ordering of terms also
    assert term == "spring"
    _, term = get_term_by_index(TERMS_INDEX_START + 1)
    assert term == "summer"
    _, term = get_term_by_index(TERMS_INDEX_START + 2)
    assert term == "autumn"
    year, term = get_term_by_index(TERMS_INDEX_START +
                                   len(SemesterTypes.choices))
    assert year == FOUNDATION_YEAR + 1
    assert term == "spring"
    year, term = get_term_by_index(TERMS_INDEX_START +
                                   2 * len(SemesterTypes.choices))
    assert year == FOUNDATION_YEAR + 2
    assert term == "spring"


def test_get_term_index_academic_year_starts():
    # Indexing starts from 1 of foundation year spring.
    with pytest.raises(ValueError):
        first_term_in_academic_year(FOUNDATION_YEAR,
                                    SemesterTypes.SPRING)
    assert 3 == first_term_in_academic_year(FOUNDATION_YEAR,
                                            SemesterTypes.AUTUMN)
    assert 3 == first_term_in_academic_year(FOUNDATION_YEAR + 1,
                                            SemesterTypes.SPRING)
    assert 6 == first_term_in_academic_year(FOUNDATION_YEAR + 1,
                                            SemesterTypes.AUTUMN)
    assert 6 == first_term_in_academic_year(FOUNDATION_YEAR + 2,
                                            SemesterTypes.SUMMER)


@pytest.mark.django_db
def test_get_current_semester_pair(settings, mocker):
    settings.TIME_ZONE = 'Etc/UTC'
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    msk_tz = pytz.timezone("Europe/Moscow")
    mocked_timezone.return_value = msk_tz.localize(
        datetime.datetime(2014, 4, 1, 12, 0))
    assert (2014, 'spring') == get_current_term_pair(msk_tz)
    mocked_timezone.return_value = msk_tz.localize(
        datetime.datetime(2015, 11, 1, 12, 0))
    assert (2015, 'autumn') == get_current_term_pair(msk_tz)
