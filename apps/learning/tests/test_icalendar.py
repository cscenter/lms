from itertools import chain

import pytest
from django.conf import settings
from icalendar import Calendar, Event

from core.urls import reverse
from courses.tests.factories import CourseFactory, CourseClassFactory, \
    AssignmentFactory
from learning.settings import Branches
from learning.tests.factories import EnrollmentFactory, EventFactory
from users.constants import Roles
from users.models import User
from users.tests.factories import UserFactory, StudentFactory


# TODO: убедиться, что для заданий/занятий учитывается таймзона пользователя из URL календаря, а не залогиненного
# TODO: для событий - пока залогиненного


@pytest.mark.django_db
def test_smoke(client, curator, settings):
    """Any user can view icalendar since these urls are not secret"""
    student = StudentFactory()
    response = client.get(student.get_classes_icalendar_url())
    assert response.status_code == 200
    response = client.get(student.get_assignments_icalendar_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_course_classes(client):
    user = StudentFactory(groups=[Roles.TEACHER])
    client.login(user)
    fname = 'csc_classes.ics'
    # Empty calendar
    response = client.get(user.get_classes_icalendar_url())
    assert response['content-type'] == "text/calendar; charset=UTF-8"
    assert fname in response['content-disposition']
    cal = Calendar.from_ical(response.content)
    assert "Занятия CSC" == cal['X-WR-CALNAME']
    # Create some content
    ccs_teaching = (CourseClassFactory
                    .create_batch(2, course__teachers=[user]))
    course = CourseFactory.create()
    EnrollmentFactory.create(student=user, course=course)
    ccs_learning = (CourseClassFactory
                    .create_batch(3, course=course))
    ccs_other = CourseClassFactory.create_batch(5)
    response = client.get(user.get_classes_icalendar_url())
    cal = Calendar.from_ical(response.content)
    cal_events = {evt['SUMMARY'] for evt in
                  cal.subcomponents if isinstance(evt, Event)}
    for cc in ccs_learning:
        assert cc.name in cal_events
    for cc in ccs_teaching:
        assert cc.name in cal_events


@pytest.mark.django_db
def test_assignments(client):
    user = StudentFactory(groups=[Roles.TEACHER],
                          branch__code=Branches.SPB)
    client.login(user)
    fname = 'csc_assignments.ics'
    # Empty calendar
    resp = client.get(user.get_assignments_icalendar_url())
    assert "text/calendar; charset=UTF-8" == resp['content-type']
    assert fname in resp['content-disposition']
    cal = Calendar.from_ical(resp.content)
    assert "Задания CSC" == cal['X-WR-CALNAME']
    # Create some content
    as_teaching = (AssignmentFactory
                   .create_batch(2, course__teachers=[user]))
    co_learning = CourseFactory.create()
    EnrollmentFactory.create(student=user, course=co_learning)
    as_learning = (AssignmentFactory
                   .create_batch(3, course=co_learning))
    as_other = AssignmentFactory.create_batch(5)
    resp = client.get(user.get_assignments_icalendar_url())
    cal = Calendar.from_ical(resp.content)
    assert {f"{a.title} ({a.course.meta_course.name})" for a in
            chain(as_teaching, as_learning)} == {
        evt['SUMMARY'] for evt in cal.subcomponents if isinstance(evt, Event)}


@pytest.mark.django_db
def test_events(client):
    file_name = 'csc_events.ics'
    url = reverse('ical_events', subdomain=settings.LMS_SUBDOMAIN)
    # Empty calendar
    response = client.get(url)
    assert "text/calendar; charset=UTF-8" == response['content-type']
    assert file_name in response['content-disposition']
    cal = Calendar.from_ical(response.content)
    assert "События CSC" == cal['X-WR-CALNAME']
    # Create some content
    nces = EventFactory.create_batch(3)
    response = client.get(url)
    cal = Calendar.from_ical(response.content)
    assert set(nce.name for nce in nces) == set(evt['SUMMARY']
                                                for evt in cal.subcomponents
                                                if isinstance(evt, Event))
