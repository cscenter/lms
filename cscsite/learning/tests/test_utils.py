# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from io import BytesIO

import pytest
import pytz
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_bytes
from mock import patch, MagicMock

from learning.management.imports import ImportGradesByStepicID
from learning.settings import (TERMS_INDEX_START, FOUNDATION_YEAR)
from learning.utils import split_on_condition, get_term_index, get_term_index_academic
from users.factories import TeacherCenterFactory, StudentCenterFactory
from ..factories import *


class UtilTests(TestCase):
    @override_settings(TIME_ZONE='Etc/UTC')
    @patch('django.utils.timezone.now')
    def test_get_current_semester_pair(self, now_mock):
        utc_tz = pytz.timezone("Etc/UTC")
        now_mock.return_value \
            = utc_tz.localize(datetime.datetime(2014, 4, 1, 12, 0))
        self.assertEquals((2014, 'spring'), get_current_semester_pair())
        now_mock.return_value \
            = utc_tz.localize(datetime.datetime(2015, 11, 1, 12, 0))
        self.assertEquals((2015, 'autumn'), get_current_semester_pair())

    def test_split_list(self):
        xs = [1, 2, 3, 4]
        self.assertEquals(([1, 3], [2, 4]),
                          split_on_condition(xs, lambda x: x % 2 != 0))
        self.assertEquals((xs, []), split_on_condition(xs, lambda x: True))
        self.assertEquals(([], xs), split_on_condition(xs, lambda x: False))

    @patch('django.contrib.messages.api.add_message')
    def test_import_stepic(self, mock_messages):
        teacher = TeacherCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        student = StudentCenterFactory()
        student.stepic_id = 20
        student.save()
        EnrollmentFactory.create(student=student, course_offering=co)
        assignments = AssignmentFactory.create_batch(3, course_offering=co)
        assignment = assignments[0]
        expected_grade = 13
        csv_input = force_bytes("user_id,total\n"
                                "{},{}\n".format(student.stepic_id,
                                                 expected_grade))
        request = MagicMock()
        request.FILES = {'csv_file': BytesIO(csv_input)}
        ImportGradesByStepicID(request, assignment).process()
        a_s = StudentAssignment.objects.get(student=student,
                                            assignment=assignment)
        self.assertEquals(a_s.grade, expected_grade)


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


def test_get_term_index_academic():
    # Indexing starts from 1 of foundation year spring.
    assert 3 == get_term_index_academic(FOUNDATION_YEAR,
                                        SEMESTER_TYPES.autumn,
                                        rewind_years=1)
    assert 6 == get_term_index_academic(FOUNDATION_YEAR + 1,
                                        SEMESTER_TYPES.autumn,
                                        rewind_years=1)
    # target year < FOUNDATION_YEAR
    with pytest.raises(ValueError):
        get_term_index_academic(FOUNDATION_YEAR,
                                SEMESTER_TYPES.spring,
                                rewind_years=1)
    assert 3 == get_term_index_academic(FOUNDATION_YEAR + 1,
                                        SEMESTER_TYPES.spring,
                                        rewind_years=1)
    assert 3 == get_term_index_academic(FOUNDATION_YEAR + 2,
                                        SEMESTER_TYPES.summer,
                                        rewind_years=2)
