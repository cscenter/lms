# -*- coding: utf-8 -*-

import unittest

from django.test import TestCase

from courses.factories import SemesterFactory
from learning.factories import *
from users.constants import AcademicRoles
from learning.tests.mixins import *
from users.factories import UserFactory


class CourseSecurityTests(MyUtilitiesMixin, TestCase):
    def test_list_center_site(self):
        """Сlub students can't see center courses"""
        current_semester = SemesterFactory.create_current()
        co_center = CourseFactory(semester=current_semester,
                                  is_open=False,
                                  city=settings.DEFAULT_CITY_CODE)
        co_spb = CourseFactory(semester=current_semester,
                               is_open=True,
                               city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseFactory.create(semester=current_semester,
                                      city="kzn")
        resp = self.client.get(reverse('course_list'))
        self.assertNotContains(resp, co_center.meta_course.name)
        self.assertContains(resp, co_spb.meta_course.name)
        self.assertNotContains(resp, co_kzn.meta_course.name)

    def test_student_list_center_site(self):
        s = UserFactory.create(groups=[AcademicRoles.STUDENT_CENTER])
        self.doLogin(s)
        current_semester = SemesterFactory.create_current()
        co_center = CourseFactory(semester=current_semester,
                                  is_open=False,
                                  city=settings.DEFAULT_CITY_CODE)
        co_spb = CourseFactory(semester=current_semester,
                               is_open=True,
                               city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseFactory.create(semester=current_semester,
                                      city="kzn")
        resp = self.client.get(reverse('course_list_student'))
        self.assertEqual(len(resp.context['ongoing_rest']), 1)

    @unittest.skip('not implemented yet')
    def test_show_news_to_all(self):
        """ On csclub site all users can see news """
        pass

