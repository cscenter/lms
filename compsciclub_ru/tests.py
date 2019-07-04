# -*- coding: utf-8 -*-

import unittest

from django.conf import settings

from core.tests.utils import CSCTestCase
from core.urls import reverse
from courses.tests.factories import *
from users.constants import AcademicRoles
from users.tests.factories import UserFactory


class CourseSecurityTests(CSCTestCase):
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
        s = UserFactory(groups=[AcademicRoles.STUDENT_CENTER])
        self.client.login(s)
        current_semester = SemesterFactory.create_current()
        co_center = CourseFactory(semester=current_semester,
                                  is_open=False,
                                  city=settings.DEFAULT_CITY_CODE)
        co_spb = CourseFactory(semester=current_semester,
                               is_open=True,
                               city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseFactory.create(semester=current_semester,
                                      city="kzn")
        resp = self.client.get(reverse('study:course_list'))
        self.assertEqual(len(resp.context['ongoing_rest']), 1)

    @unittest.skip('not implemented yet')
    def test_show_news_to_all(self):
        """ On csclub site all users can see news """
        pass

