# -*- coding: utf-8 -*-
import pytest
import pytz
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch, MagicMock

from learning.settings import (TERMS_INDEX_START, FOUNDATION_YEAR)
from learning.utils import split_on_condition, get_term_index, \
    get_term_index_academic_year_starts
from ..factories import *


class UtilTests(TestCase):
    @override_settings(TIME_ZONE='Etc/UTC')
    @patch('django.utils.timezone.now')
    def test_get_current_semester_pair(self, now_mock):
        msk_tz = pytz.timezone("Europe/Moscow")
        now_mock.return_value = msk_tz.localize(
            datetime.datetime(2014, 4, 1, 12, 0))
        self.assertEquals((2014, 'spring'), get_current_term_pair('spb'))
        now_mock.return_value = msk_tz.localize(
            datetime.datetime(2015, 11, 1, 12, 0))
        self.assertEquals((2015, 'autumn'), get_current_term_pair('spb'))

    def test_split_list(self):
        xs = [1, 2, 3, 4]
        self.assertEquals(([1, 3], [2, 4]),
                          split_on_condition(xs, lambda x: x % 2 != 0))
        self.assertEquals((xs, []), split_on_condition(xs, lambda x: True))
        self.assertEquals(([], xs), split_on_condition(xs, lambda x: False))


def test_get_term_index():
    cnt = len(SEMESTER_TYPES)
    with pytest.raises(ValueError) as e:
        get_term_index(FOUNDATION_YEAR - 1, SEMESTER_TYPES.spring)
    assert "target year < FOUNDATION_YEAR" in str(e.value)
    with pytest.raises(ValueError) as e:
        get_term_index(FOUNDATION_YEAR, "sprEng")
    assert "unknown term type" in str(e.value)
    assert get_term_index(FOUNDATION_YEAR,
                          SEMESTER_TYPES.spring) == TERMS_INDEX_START
    assert get_term_index(FOUNDATION_YEAR,
                          SEMESTER_TYPES.summer) == TERMS_INDEX_START + 1
    assert get_term_index(FOUNDATION_YEAR,
                          SEMESTER_TYPES.autumn) == TERMS_INDEX_START + 2
    assert get_term_index(FOUNDATION_YEAR + 1,
                          SEMESTER_TYPES.spring) == TERMS_INDEX_START + cnt
    assert get_term_index(FOUNDATION_YEAR + 1,
                          SEMESTER_TYPES.summer) == TERMS_INDEX_START + cnt + 1
    assert get_term_index(FOUNDATION_YEAR + 7,
                          SEMESTER_TYPES.spring) == TERMS_INDEX_START + cnt * 7


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
    year, term = get_term_by_index(TERMS_INDEX_START + len(SEMESTER_TYPES))
    assert year == FOUNDATION_YEAR + 1
    assert term == "spring"
    year, term = get_term_by_index(TERMS_INDEX_START + 2 * len(SEMESTER_TYPES))
    assert year == FOUNDATION_YEAR + 2
    assert term == "spring"


def test_get_term_index_academic_year_starts():
    # Indexing starts from 1 of foundation year spring.
    with pytest.raises(ValueError):
        get_term_index_academic_year_starts(FOUNDATION_YEAR,
                                            SEMESTER_TYPES.spring)
    assert 3 == get_term_index_academic_year_starts(FOUNDATION_YEAR,
                                                    SEMESTER_TYPES.autumn)
    assert 3 == get_term_index_academic_year_starts(FOUNDATION_YEAR + 1,
                                                    SEMESTER_TYPES.spring)
    assert 6 == get_term_index_academic_year_starts(FOUNDATION_YEAR + 1,
                                                    SEMESTER_TYPES.autumn)
    assert 6 == get_term_index_academic_year_starts(FOUNDATION_YEAR + 2,
                                                    SEMESTER_TYPES.summer)
