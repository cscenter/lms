from itertools import chain

import pytest
from icalendar import Calendar, Event

from core.urls import reverse
from courses.tests.factories import CourseFactory, CourseClassFactory, \
    AssignmentFactory
from learning.tests.factories import EnrollmentFactory, EventFactory
from users.models import User
from users.tests.factories import UserFactory, StudentFactory


# TODO: убедиться, что для заданий/занятий учитывается таймзона пользователя из URL календаря, а не залогиненного
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
def test_classes(client):
    user = UserFactory(groups=[User.roles.STUDENT_CENTER,
                               User.roles.TEACHER_CENTER],
                       city_id='spb')
    client.login(user)
    fname = 'csc_classes.ics'
    # Empty calendar
    response = client.get(reverse('user_ical_classes', args=[user.pk]))
    assert response['content-type'] == "text/calendar; charset=UTF-8"
    assert fname in response['content-disposition']
    cal = Calendar.from_ical(response.content)
    assert "Занятия CSC" == cal['X-WR-CALNAME']
    # Create some content
    ccs_teaching = (CourseClassFactory
                    .create_batch(2, course__teachers=[user]))
    co_learning = CourseFactory.create()
    EnrollmentFactory.create(student=user, course=co_learning)
    ccs_learning = (CourseClassFactory
                    .create_batch(3, course=co_learning))
    ccs_other = CourseClassFactory.create_batch(5)
    response = client.get(reverse('user_ical_classes', args=[user.pk]))
    cal = Calendar.from_ical(response.content)
    assert {cc.name for cc in chain(ccs_teaching, ccs_learning)} == {
        evt['SUMMARY'] for evt in cal.subcomponents if isinstance(evt, Event)}


@pytest.mark.django_db
def test_assignments(client):
    user = UserFactory(groups=[User.roles.STUDENT_CENTER,
                               User.roles.TEACHER_CENTER],
                       city_id='spb')
    client.login(user)
    fname = 'csc_assignments.ics'
    # Empty calendar
    resp = client.get(reverse('user_ical_assignments', args=[user.pk]))
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
    resp = client.get(reverse('user_ical_assignments', args=[user.pk]))
    cal = Calendar.from_ical(resp.content)
    assert {f"{a.title} ({a.course.meta_course.name})" for a in
            chain(as_teaching, as_learning)} == {
        evt['SUMMARY'] for evt in cal.subcomponents if isinstance(evt, Event)}


@pytest.mark.django_db
def test_events(client):
    file_name = 'csc_events.ics'
    # Empty calendar
    response = client.get(reverse('ical_events'))
    assert "text/calendar; charset=UTF-8" == response['content-type']
    assert file_name in response['content-disposition']
    cal = Calendar.from_ical(response.content)
    assert "События CSC" == cal['X-WR-CALNAME']
    # Create some content
    nces = EventFactory.create_batch(3)
    response = client.get(reverse('ical_events'))
    cal = Calendar.from_ical(response.content)
    assert set(nce.name for nce in nces) == set(evt['SUMMARY']
                                                for evt in cal.subcomponents
                                                if isinstance(evt, Event))
