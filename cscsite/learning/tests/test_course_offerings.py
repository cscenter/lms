import datetime
import pytest
import pytz
from typing import Optional

from bs4 import BeautifulSoup
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from learning.factories import CourseFactory, SemesterFactory, \
    CourseOfferingFactory, CourseOfferingNewsFactory, AssignmentFactory, \
    CourseOfferingTeacherFactory
from learning.models import Semester
from learning.settings import PARTICIPANT_GROUPS
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


# Test timezones


TEST_YEAR = 2017


def get_timezone_gmt_offset(tz: pytz.timezone) -> Optional[datetime.timedelta]:
    return tz.localize(datetime.datetime(TEST_YEAR, 1, 1)).utcoffset()


SPB_OFFSET = get_timezone_gmt_offset(settings.TIME_ZONES['spb'])
NSK_OFFSET = get_timezone_gmt_offset(settings.TIME_ZONES['nsk'])


@pytest.mark.django_db
def test_news_get_city_timezone(settings):
    news = CourseOfferingNewsFactory(course_offering__city_id='nsk')
    assert news.get_city_timezone() == settings.TIME_ZONES['nsk']
    news.course_offering.city_id = 'spb'
    news.refresh_from_db()
    assert news.get_city_timezone() == settings.TIME_ZONES['spb']


@pytest.mark.django_db
def test_course_offering_news(settings, admin_client):
    settings.LANGUAGE_CODE = 'ru'
    news = CourseOfferingNewsFactory(course_offering__city_id='spb',
                                     created=datetime.datetime(TEST_YEAR, 1, 13,
                                                               20, 0, 0, 0,
                                                               tzinfo=pytz.UTC))
    co = news.course_offering
    date_in_utc = news.created
    localized = date_in_utc.astimezone(settings.TIME_ZONES['spb'])
    assert localized.utcoffset() == datetime.timedelta(
        seconds=SPB_OFFSET.total_seconds())
    assert localized.hour == 23
    date_str = "{:02d}".format(localized.day)
    assert date_str == "13"
    response = admin_client.get(co.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any(date_str in s.string for s in
               html.find_all('div', {"class": "date"}))
    # For NSK we should live in the next day
    co.city_id = 'nsk'
    co.save()
    localized = date_in_utc.astimezone(settings.TIME_ZONES['nsk'])
    assert localized.utcoffset() == datetime.timedelta(
        seconds=NSK_OFFSET.total_seconds())
    assert localized.hour == 3
    assert localized.day == 14
    date_str = "{:02d}".format(localized.day)
    assert date_str == "14"
    response = admin_client.get(co.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any(date_str in s.string for s in
               html.find_all('div', {"class": "date"}))


@pytest.mark.django_db
def test_course_offering_is_correspondence(settings, client):
    """Test how `tz_override` works with different user roles"""
    # 12 january 2017 23:59 (local time)
    deadline_at = datetime.datetime(TEST_YEAR, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    assignment = AssignmentFactory(deadline_at=deadline_at,
                                   course_offering__city_id='spb',
                                   course_offering__is_correspondence=False)
    teacher_nsk = TeacherCenterFactory(city_id='nsk')
    student_spb = StudentCenterFactory(city_id='spb')
    student_nsk = StudentCenterFactory(city_id='nsk')
    co = assignment.course_offering
    # Unauthenticated user doesn't see tab
    url = co.get_url_for_tab("assignments")
    response = client.get(url)
    assert response.status_code == 302
    # Any authenticated user for offline courses see timezone of the course
    for u in [student_spb, student_nsk, teacher_nsk]:
        client.login(u)
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["tz_override"] is None
    co.is_correspondence = True
    co.save()
    # Any authenticated user (this teacher is not actual teacher of the course)
    client.login(teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    client.login(student_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    client.login(student_spb)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['spb']
    # Actual teacher of the course
    CourseOfferingTeacherFactory(course_offering=co, teacher=teacher_nsk)
    client.login(teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None
    # Teacher without city, fallback to course offering timezone
    teacher = TeacherCenterFactory()
    assert teacher.city_id is None
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None


@pytest.mark.django_db
def test_course_offering_assignment_timezone(settings, client):
    """
    Teacher of the course always must see timezone of course offering,
    even if he is also learning in CS Center.
    """
    teacher_nsk = TeacherCenterFactory(city_id='nsk')
    # 12 january 2017 23:59 (local time)
    deadline_at = datetime.datetime(TEST_YEAR, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    assignment = AssignmentFactory(deadline_at=deadline_at,
                                   course_offering__city_id='spb',
                                   course_offering__is_correspondence=True)
    co = assignment.course_offering
    client.login(teacher_nsk)
    url = co.get_url_for_tab("assignments")
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    teacher_nsk.groups.add(PARTICIPANT_GROUPS.STUDENT_CENTER)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    # Don't override timezone if current authenticated user is actual teacher of
    # the course
    CourseOfferingTeacherFactory(course_offering=co, teacher=teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None
