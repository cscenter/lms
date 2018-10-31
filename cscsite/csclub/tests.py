# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import unittest

import pytest
from bs4 import BeautifulSoup

from django.conf import settings
from django.urls import reverse
from django.test import TestCase

from learning.factories import *
from users.factories import UserFactory
from learning.tests.mixins import *


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
        s = UserFactory.create(groups=[PARTICIPANT_GROUPS.STUDENT_CENTER])
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

