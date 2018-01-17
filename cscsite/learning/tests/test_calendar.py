import datetime

import pytest
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from learning.factories import CourseClassFactory, NonCourseEventFactory, \
    CourseOfferingFactory, EnrollmentFactory
from learning.settings import PARTICIPANT_GROUPS
from learning.tests.mixins import MyUtilitiesMixin
from learning.tests.test_views import GroupSecurityCheckMixin
from learning.tests.utils import flatten_calendar_month_events
from users.factories import UserFactory, StudentCenterFactory, \
    TeacherCenterFactory


# TODO: add test: kzn courses not shown on center site and spb on kzn
# TODO: add test: summer courses not shown on club site on main page

# TODO: убедиться, что город берётся из настроек для студента (get_student_city_code
# TODO: для СПБ не показываются события НСК (наоборот будет уже верно)
# TODO: тестировать CourseClassQuerySet manager
# TODO: тестировать границы для месяца
# TODO: тестировать now_local?
# TODO: тестировать CalendarData


class CalendarTeacherTests(GroupSecurityCheckMixin,
                           MyUtilitiesMixin, TestCase):
    url_name = 'calendar_teacher'
    groups_allowed = [PARTICIPANT_GROUPS.TEACHER_CENTER]

    def test_teacher_calendar(self):
        teacher = TeacherCenterFactory()
        other_teacher = TeacherCenterFactory()
        self.doLogin(teacher)
        classes = flatten_calendar_month_events(
            self.client.get(reverse(self.url_name)).context['events'])
        assert len(classes) == 0
        this_month_date = (datetime.datetime.now()
                           .replace(day=15,
                                    tzinfo=timezone.utc))
        own_classes = (
            CourseClassFactory
            .create_batch(3, course_offering__teachers=[teacher],
                          date=this_month_date))
        others_classes = (
            CourseClassFactory
            .create_batch(5, course_offering__teachers=[other_teacher],
                          date=this_month_date))
        events = (
            NonCourseEventFactory
            .create_batch(2, date=this_month_date))
        # teacher should see only his own classes and non-course events
        resp = self.client.get(reverse(self.url_name))
        classes = flatten_calendar_month_events(resp.context['events'])
        self.assertSameObjects(own_classes + events, classes)
        # but in full calendar all classes should be shown
        classes = flatten_calendar_month_events(
            self.client.get(reverse('calendar_full_teacher')).context['events'])
        self.assertSameObjects(own_classes + others_classes + events, classes)
        next_month_qstr = (
            "?year={0}&month={1}"
            .format(resp.context['next'].year,
                    str(resp.context['next'].month).zfill(2)))
        next_month_url = reverse(self.url_name) + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        classes = flatten_calendar_month_events(
            self.client.get(next_month_url).context['events'])
        self.assertSameObjects([], classes)
        next_month_date = this_month_date + relativedelta(months=1)
        next_month_classes = (
            CourseClassFactory
            .create_batch(2, course_offering__teachers=[teacher],
                          date=next_month_date))
        classes = flatten_calendar_month_events(
            self.client.get(next_month_url).context['events'])
        self.assertSameObjects(next_month_classes, classes)


class CalendarStudentTests(GroupSecurityCheckMixin,
                           MyUtilitiesMixin, TestCase):
    url_name = 'calendar_student'
    groups_allowed = [PARTICIPANT_GROUPS.STUDENT_CENTER]

    def test_student_calendar(self):
        student = StudentCenterFactory(city_id='spb')
        self.doLogin(student)
        co = CourseOfferingFactory.create()
        co_other = CourseOfferingFactory.create()
        e = EnrollmentFactory.create(course_offering=co, student=student)
        classes = flatten_calendar_month_events(
            self.client.get(reverse(self.url_name)).context['events'])
        self.assertEqual(0, len(classes))
        this_month_date = (datetime.datetime.now()
                           .replace(day=15,
                                    tzinfo=timezone.utc))
        own_classes = (
            CourseClassFactory
            .create_batch(3, course_offering=co, date=this_month_date))
        others_classes = (
            CourseClassFactory
            .create_batch(5, course_offering=co_other, date=this_month_date))
        # student should see only his own classes
        resp = self.client.get(reverse(self.url_name))
        classes = flatten_calendar_month_events(resp.context['events'])
        self.assertSameObjects(own_classes, classes)
        # but in full calendar all classes should be shown
        classes = flatten_calendar_month_events(
            self.client.get(reverse('calendar_full_student')).context['events'])
        self.assertSameObjects(own_classes + others_classes, classes)
        next_month_qstr = (
            "?year={0}&month={1}"
            .format(resp.context['next'].year,
                    str(resp.context['next'].month).zfill(2)))
        next_month_url = reverse(self.url_name) + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        classes = flatten_calendar_month_events(
            self.client.get(next_month_url).context['events'])
        self.assertSameObjects([], classes)
        next_month_date = this_month_date + relativedelta(months=1)
        next_month_classes = (
            CourseClassFactory
            .create_batch(2, course_offering=co, date=next_month_date))
        classes = flatten_calendar_month_events(
            self.client.get(next_month_url).context['events'])
        self.assertSameObjects(next_month_classes, classes)


class CalendarFullSecurityTests(MyUtilitiesMixin, TestCase):
    """
    This TestCase is used only for security check, actual tests for
    "full calendar" are done in CalendarTeacher/CalendarStudent tests
    """
    def test_full_calendar_security(self):
        u = StudentCenterFactory(city_id='spb')
        url = 'calendar_full_student'
        self.assertLoginRedirect(reverse(url))
        self.doLogin(u)
        self.assertStatusCode(200, url)
        self.client.logout()
        # For teacher role we can skip city setting
        u = TeacherCenterFactory()
        self.doLogin(u)
        url = 'calendar_full_teacher'
        self.assertStatusCode(200, url)


@pytest.mark.django_db
def test_correspondence_courses_calendar(client):
    """Make sure correspondence courses are visible in main calendar"""
    student = StudentCenterFactory(city_id='spb')
    client.login(student)
    this_month_date = datetime.datetime.utcnow()
    CourseClassFactory.create_batch(
            3, course_offering__is_correspondence=True, date=this_month_date)
    classes = flatten_calendar_month_events(
        client.get(reverse("calendar_full_student")).context['events'])
    assert len(classes) == 3
