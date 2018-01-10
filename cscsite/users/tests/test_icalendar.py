from itertools import chain
import pytest
from django.test import TestCase
from django.urls import reverse
from icalendar import Calendar, Event

from learning.factories import CourseClassFactory, CourseOfferingFactory, \
    EnrollmentFactory, AssignmentFactory, NonCourseEventFactory
from learning.tests.mixins import MyUtilitiesMixin
from users.factories import UserFactory, StudentFactory
from users.models import CSCUser


class ICalTests(MyUtilitiesMixin, TestCase):
    def test_classes(self):
        user = UserFactory(groups=[CSCUser.group.STUDENT_CENTER,
                                   CSCUser.group.TEACHER_CENTER])
        self.doLogin(user)
        fname = 'csc_classes.ics'
        # Empty calendar
        response = self.client.get(reverse('user_ical_classes', args=[user.pk]))
        assert response['content-type'] == "text/calendar; charset=UTF-8"
        self.assertIn(fname, response['content-disposition'])
        cal = Calendar.from_ical(response.content)
        self.assertEquals("Занятия CSC", cal['X-WR-CALNAME'])
        # Create some content
        ccs_teaching = (CourseClassFactory
                        .create_batch(2, course_offering__teachers=[user]))
        co_learning = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=user, course_offering=co_learning)
        ccs_learning = (CourseClassFactory
                        .create_batch(3, course_offering=co_learning))
        ccs_other = CourseClassFactory.create_batch(5)
        response = self.client.get(reverse('user_ical_classes', args=[user.pk]))
        cal = Calendar.from_ical(response.content)
        self.assertSameObjects([cc.name
                                for cc in chain(ccs_teaching, ccs_learning)],
                               [evt['SUMMARY']
                                for evt in cal.subcomponents
                                if isinstance(evt, Event)])

    def test_assignments(self):
        user = UserFactory(groups=[CSCUser.group.STUDENT_CENTER,
                                   CSCUser.group.TEACHER_CENTER])
        self.doLogin(user)
        fname = 'csc_assignments.ics'
        # Empty calendar
        resp = self.client.get(reverse('user_ical_assignments', args=[user.pk]))
        self.assertEquals("text/calendar; charset=UTF-8", resp['content-type'])
        self.assertIn(fname, resp['content-disposition'])
        cal = Calendar.from_ical(resp.content)
        self.assertEquals("Задания CSC", cal['X-WR-CALNAME'])
        # Create some content
        as_teaching = (AssignmentFactory
                       .create_batch(2, course_offering__teachers=[user]))
        co_learning = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=user, course_offering=co_learning)
        as_learning = (AssignmentFactory
                       .create_batch(3, course_offering=co_learning))
        as_other = AssignmentFactory.create_batch(5)
        resp = self.client.get(reverse('user_ical_assignments', args=[user.pk]))
        cal = Calendar.from_ical(resp.content)
        self.assertSameObjects(["{} ({})".format(a.title,
                                                 a.course_offering.course.name)
                                for a in chain(as_teaching, as_learning)],
                               [evt['SUMMARY']
                                for evt in cal.subcomponents
                                if isinstance(evt, Event)])

    def test_events(self):
        file_name = 'csc_events.ics'
        # Empty calendar
        response = self.client.get(reverse('ical_events'))
        assert "text/calendar; charset=UTF-8" == response['content-type']
        self.assertIn(file_name, response['content-disposition'])
        cal = Calendar.from_ical(response.content)
        self.assertEquals("События CSC", cal['X-WR-CALNAME'])
        # Create some content
        nces = NonCourseEventFactory.create_batch(3)
        response = self.client.get(reverse('ical_events'))
        cal = Calendar.from_ical(response.content)
        self.assertSameObjects([nce.name for nce in nces],
                               [evt['SUMMARY']
                                for evt in cal.subcomponents
                                if isinstance(evt, Event)])

# TODO: убедиться, что берётся таймзона пользователя из ссылки, а не залогиненного
# TODO: для событий - пока залогиненного


@pytest.mark.django_db
def test_smoke(client, curator, settings):
    """Make sure that any user can view icalendar. We have no secret link now"""
    student = StudentFactory(city_id='kzn')
    response = client.get(student.get_classes_icalendar_url())
    assert response.status_code == 200
    response = client.get(student.get_assignments_icalendar_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_timezone(client, curator, settings):
    student = StudentFactory(city_id='kzn')
