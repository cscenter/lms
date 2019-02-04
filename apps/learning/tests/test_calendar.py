import datetime

import pytest
from dateutil.relativedelta import relativedelta
from core.tests.utils import CSCTestCase
from django.utils import timezone

from core.urls import reverse
from courses.tests.factories import CourseFactory, CourseClassFactory, \
    VenueFactory
from learning.tests.factories import EventFactory, \
    EnrollmentFactory
from learning.tests.mixins import MyUtilitiesMixin
from learning.tests.test_views import GroupSecurityCheckMixin
from learning.tests.utils import flatten_calendar_month_events
from users.constants import AcademicRoles
from users.tests.factories import StudentCenterFactory, \
    TeacherCenterFactory


# TODO: add test: kzn courses not shown on center site and spb on kzn
# TODO: add test: summer courses not shown on club site on main page

# TODO: убедиться, что город берётся из настроек для студента (get_student_city_code
# TODO: для СПБ не показываются события НСК (наоборот будет уже верно)


class CalendarTeacherTests(GroupSecurityCheckMixin,
                           MyUtilitiesMixin, CSCTestCase):
    url_name = 'teaching:calendar'
    groups_allowed = [AcademicRoles.TEACHER_CENTER]

    def test_teacher_calendar(self):
        teacher = TeacherCenterFactory(city_id='spb')
        other_teacher = TeacherCenterFactory(city_id='spb')
        self.doLogin(teacher)
        response = self.client.get(reverse(self.url_name))
        classes = flatten_calendar_month_events(response.context['calendar'])
        assert len(classes) == 0
        this_month_date = (datetime.datetime.now()
                           .replace(day=15, tzinfo=timezone.utc))
        own_classes = (
            CourseClassFactory
            .create_batch(3, course__teachers=[teacher],
                          date=this_month_date))
        others_classes = (
            CourseClassFactory
            .create_batch(5, course__teachers=[other_teacher],
                          date=this_month_date))
        venue = VenueFactory(city_id=teacher.city_id)
        events = EventFactory.create_batch(2, date=this_month_date, venue=venue)
        # teacher should see only his own classes and non-course events
        resp = self.client.get(reverse(self.url_name))
        classes = flatten_calendar_month_events(resp.context['calendar'])
        self.assertSameObjects(own_classes + events, classes)
        # No events on the next month
        next_month_qstr = (
            "?year={0}&month={1}"
            .format(resp.context['calendar'].next_month.year,
                    str(resp.context['calendar'].next_month.month)))
        next_month_url = reverse(self.url_name) + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        classes = flatten_calendar_month_events(
            self.client.get(next_month_url).context['calendar'])
        self.assertSameObjects([], classes)
        # Add some and test
        next_month_date = this_month_date + relativedelta(months=1)
        next_month_classes = (
            CourseClassFactory
            .create_batch(2, course__teachers=[teacher],
                          date=next_month_date))
        classes = flatten_calendar_month_events(
            self.client.get(next_month_url).context['calendar'])
        self.assertSameObjects(next_month_classes, classes)
        # On a full calendar all classes should be shown
        response = self.client.get(reverse('teaching:calendar_full'))
        classes = flatten_calendar_month_events(response.context['calendar'])
        self.assertSameObjects(own_classes + others_classes + events, classes)


class CalendarStudentTests(GroupSecurityCheckMixin,
                           MyUtilitiesMixin, CSCTestCase):
    url_name = 'study:calendar'
    groups_allowed = [AcademicRoles.STUDENT_CENTER]

    def test_student_calendar(self):
        student = StudentCenterFactory(city_id='spb')
        self.doLogin(student)
        co = CourseFactory.create()
        co_other = CourseFactory.create()
        e = EnrollmentFactory.create(course=co, student=student)
        classes = flatten_calendar_month_events(
            self.client.get(reverse(self.url_name)).context['calendar'])
        self.assertEqual(0, len(classes))
        this_month_date = (datetime.datetime.now()
                           .replace(day=15,
                                    tzinfo=timezone.utc))
        own_classes = (
            CourseClassFactory
            .create_batch(3, course=co, date=this_month_date))
        others_classes = (
            CourseClassFactory
            .create_batch(5, course=co_other, date=this_month_date))
        # student should see only his own classes
        resp = self.client.get(reverse(self.url_name))
        classes = flatten_calendar_month_events(resp.context['calendar'])
        self.assertSameObjects(own_classes, classes)
        # but in full calendar all classes should be shown
        classes = flatten_calendar_month_events(
            self.client.get(reverse('study:calendar_full')).context['calendar'])
        self.assertSameObjects(own_classes + others_classes, classes)
        next_month_qstr = (
            "?year={0}&month={1}"
            .format(resp.context['calendar'].next_month.year,
                    str(resp.context['calendar'].next_month.month)))
        next_month_url = reverse(self.url_name) + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        classes = flatten_calendar_month_events(
            self.client.get(next_month_url).context['calendar'])
        self.assertSameObjects([], classes)
        next_month_date = this_month_date + relativedelta(months=1)
        next_month_classes = (
            CourseClassFactory
            .create_batch(2, course=co, date=next_month_date))
        classes = flatten_calendar_month_events(
            self.client.get(next_month_url).context['calendar'])
        self.assertSameObjects(next_month_classes, classes)
        venue = VenueFactory(city_id=student.city_id)
        events = EventFactory.create_batch(2, date=this_month_date, venue=venue)
        response = self.client.get(reverse(self.url_name))
        assert response.status_code == 200


class CalendarFullSecurityTests(MyUtilitiesMixin, CSCTestCase):
    """
    This TestCase is used only for security check, actual tests for
    "full calendar" are done in CalendarTeacher/CalendarStudent tests
    """
    def test_full_calendar_security(self):
        u = StudentCenterFactory(city_id='spb')
        url = 'study:calendar_full'
        self.assertLoginRedirect(reverse(url))
        self.doLogin(u)
        self.assertStatusCode(200, url)
        self.client.logout()
        # For teacher role we can skip city setting
        u = TeacherCenterFactory()
        self.doLogin(u)
        url = 'teaching:calendar_full'
        self.assertStatusCode(200, url)


@pytest.mark.django_db
def test_correspondence_courses_in_a_full_calendar(client):
    """Make sure correspondence courses are visible in a full calendar"""
    student = StudentCenterFactory(city_id='spb')
    client.login(student)
    this_month_date = datetime.datetime.utcnow()
    CourseClassFactory.create_batch(
            3, course__is_correspondence=True, date=this_month_date)
    classes = flatten_calendar_month_events(
        client.get(reverse("study:calendar_full")).context['calendar'])
    assert len(classes) == 3
    teacher = TeacherCenterFactory(city_id='spb')
    client.login(teacher)
    classes = flatten_calendar_month_events(
        client.get(reverse("teaching:calendar_full")).context['calendar'])
    assert len(classes) == 3
