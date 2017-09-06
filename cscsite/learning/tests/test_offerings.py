import pytest
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from learning.factories import CourseFactory, SemesterFactory, \
    CourseOfferingFactory
from learning.models import Semester
from learning.tests.mixins import MyUtilitiesMixin
from users.factories import TeacherCenterFactory, StudentCenterFactory


class SemesterListTests(MyUtilitiesMixin, TestCase):
    def cos_from_semester_list(self, lst):
        return sum([semester.courseofferings
                    for pair in lst
                    for semester in pair
                    if semester], [])

    @pytest.mark.skip(reason="Fix with empty list?")
    def test_semester_list(self):
        cos = self.cos_from_semester_list(
            self.client.get(reverse('course_list'))
            .context['semester_list'])
        self.assertEqual(0, len(cos))
        # Microoptimization: avoid creating teachers/courses
        u = TeacherCenterFactory()
        c = CourseFactory.create()
        for semester_type in ['autumn', 'spring']:
            for year in range(2012, 2015):
                s = SemesterFactory.create(type=semester_type,
                                           year=year)
                CourseOfferingFactory.create(course=c, semester=s,
                                             teachers=[u])
        s = SemesterFactory.create(type='autumn', year=2015)
        CourseOfferingFactory.create(course=c, semester=s, teachers=[u])
        resp = self.client.get(reverse('course_list'))
        self.assertEqual(4, len(resp.context['semester_list']))
        cos = self.cos_from_semester_list(resp.context['semester_list'])
        self.assertEqual(7, len(cos))


class CourseOfferingMultiSiteSecurityTests(MyUtilitiesMixin, TestCase):
    def test_list_center_site(self):
        """Center students can see club CO only from SPB"""
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseOfferingFactory.create(semester=s,
                                          city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseOfferingFactory.create(semester=s,
                                              city="kzn")
        resp = self.client.get(reverse('course_list'))
        # Really stupid test, we filter summer courses on /courses/ page
        if s.type != Semester.TYPES.summer:
            self.assertContains(resp, co.course.name)
            self.assertNotContains(resp, co_kzn.course.name)
        # Note: Club related tests in csclub app

    def test_student_list_center_site(self):
        student = StudentCenterFactory(city_id=settings.DEFAULT_CITY_CODE)
        self.doLogin(student)
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseOfferingFactory.create(semester=s,
                                          city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseOfferingFactory.create(semester=s, city="kzn")
        response = self.client.get(reverse('course_list_student'))
        self.assertEqual(len(response.context['ongoing_rest']), 1)