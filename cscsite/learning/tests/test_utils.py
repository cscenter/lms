# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import cStringIO
import datetime

from mock import patch, MagicMock
import pytz

from django.test import TestCase
from django.test.utils import override_settings

from learning.utils import get_current_semester_pair, split_list, import_stepic
from .factories import *


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
                          split_list(xs, lambda x: x % 2 != 0))
        self.assertEquals((xs, []), split_list(xs, lambda x: True))
        self.assertEquals(([], xs), split_list(xs, lambda x: False))


    @patch('django.contrib.messages.error')
    def test_import_stepic(self, mock_messages):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        student = UserFactory.create(groups=['Student [CENTER]'])
        student.stepic_id = 20
        student.save()
        EnrollmentFactory.create(student=student, course_offering=co)
        assignments = AssignmentFactory.create_batch(3, course_offering=co)
        assignment = assignments[0]
        expected_grade = 13
        csv_input = ('user_id,всего\n' + 
                      str(student.stepic_id) + ',' + str(expected_grade) +
                      '\n').encode('utf-8')
        request = MagicMock()
        request.FILES = {'csvfile': cStringIO.StringIO(csv_input)}
        import_stepic(request, assignment)
        a_s = AssignmentStudent.objects.get(student=student,
                                            assignment=assignment)
        self.assertEquals(a_s.grade, expected_grade)