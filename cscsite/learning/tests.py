# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime

from django.test import TestCase

from .models import Course, Semester, CourseOffering


class CourseOfferingTests(TestCase):
    def test_is_ongoing(self):
        """
        In near future only one course should be "ongoing".
        """
        future_year = datetime.datetime.now().year + 20
        semesters = (Semester(year=year,
                              type=Semester.TYPES[t])
                     for t in ['spring', 'autumn']
                     for year in range(2010, future_year))
        n_ongoing = sum((CourseOffering(course=Course(name="Test course"),
                                        semester=semester)
                         .is_ongoing)
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
