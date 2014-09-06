# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime

from django.test import TestCase

from .models import Course, Semester, CourseOffering, Assignment, \
    AssignmentStudent


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


class AssignmentStudentTests(TestCase):
    def test_state(self):
        a_online = Assignment(grade_min=5, grade_max=10, is_online=True)
        a_offline = Assignment(grade_min=5, grade_max=10, is_online=False)
        a_s = AssignmentStudent(assignment=a_online, grade=0)
        self.assertEqual(a_s.state, 'unsatisfactory')
        a_s = AssignmentStudent(assignment=a_online, grade=4)
        self.assertEqual(a_s.state, 'unsatisfactory')
        a_s = AssignmentStudent(assignment=a_online, grade=5)
        self.assertEqual(a_s.state, 'pass')
        a_s = AssignmentStudent(assignment=a_online, grade=10)
        self.assertEqual(a_s.state, 'excellent')
        a_s = AssignmentStudent(assignment=a_online)
        self.assertEqual(a_s.state, 'not_submitted')
        a_s = AssignmentStudent(assignment=a_offline)
        self.assertEqual(a_s.state, 'not_checked')
