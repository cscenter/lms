from itertools import chain

import pytest
from icalendar import Calendar, Event

from django.contrib.sites.models import Site

from admission.constants import InterviewSections
from admission.tests.factories import InterviewFactory
from core.urls import reverse
from courses.tests.factories import AssignmentFactory, CourseClassFactory, CourseFactory
from learning.settings import Branches
from learning.tests.factories import EnrollmentFactory, EventFactory
from users.constants import Roles
from users.tests.factories import StudentFactory, UserFactory

# TODO: убедиться, что для заданий/занятий учитывается таймзона пользователя из URL календаря, а не залогиненного
# TODO: для событий - пока залогиненного


@pytest.mark.django_db
def test_smoke(client, curator, settings):
    """User can view only own icalendar since these urls are secret"""
    student = StudentFactory()
    other_student = StudentFactory()
    client.login(student)
    response = client.get(student.get_classes_icalendar_url())
    assert response.status_code == 200
    response = client.get(student.get_assignments_icalendar_url())
    assert response.status_code == 200
    response = client.get(other_student.get_assignments_icalendar_url())
    assert response.status_code == 302
    assert response.url.startswith('/login')


@pytest.mark.django_db
def test_course_classes(client, settings, mocker):
    mocker.patch('code_reviews.gerrit.tasks.update_password_in_gerrit')
    user = StudentFactory(groups=[Roles.TEACHER])
    client.login(user)
    fname = 'classes.ics'
    # Empty calendar
    response = client.get(user.get_classes_icalendar_url())
    assert response['content-type'] == "text/calendar; charset=UTF-8"
    assert fname in response['content-disposition']
    cal = Calendar.from_ical(response.content)
    site = Site.objects.get(pk=settings.SITE_ID)
    assert f"Занятия {site.name}" == cal['X-WR-CALNAME']
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
def test_assignments(client, settings, mocker):
    mocker.patch('code_reviews.gerrit.tasks.update_password_in_gerrit')
    user = StudentFactory(groups=[Roles.TEACHER],
                          branch__code=Branches.SPB)
    client.login(user)
    fname = 'assignments.ics'
    # Empty calendar
    resp = client.get(user.get_assignments_icalendar_url())
    assert "text/calendar; charset=UTF-8" == resp['content-type']
    assert fname in resp['content-disposition']
    cal = Calendar.from_ical(resp.content)
    site = Site.objects.get(pk=settings.SITE_ID)
    assert f"Задания {site.name}" == cal['X-WR-CALNAME']
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
def test_interviews(client, settings, mocker):
    user = UserFactory(groups=[Roles.INTERVIEWER])
    client.login(user)
    fname = 'interviews.ics'
    # Empty calendar
    url = reverse('user_ical_interviews', args=[user.pk],
                  subdomain=settings.LMS_SUBDOMAIN)
    resp = client.get(url)
    assert "text/calendar; charset=UTF-8" == resp['content-type']
    assert fname in resp['content-disposition']
    cal = Calendar.from_ical(resp.content)
    site = Site.objects.get(pk=settings.SITE_ID)
    assert f"Собеседования {site.name}" == cal['X-WR-CALNAME']
    InterviewFactory.create_batch(2, interviewers=[user], section=InterviewSections.MATH)
    resp = client.get(url)
    cal = Calendar.from_ical(resp.content)
    assert len([evt for evt in cal.subcomponents if isinstance(evt, Event)]) == 2


@pytest.mark.django_db
def test_events(client, settings):
    file_name = 'events.ics'
    url = reverse('ical_events', subdomain=settings.LMS_SUBDOMAIN)
    # Empty calendar
    response = client.get(url)
    assert "text/calendar; charset=UTF-8" == response['content-type']
    assert file_name in response['content-disposition']
    cal = Calendar.from_ical(response.content)
    site = Site.objects.get(pk=settings.SITE_ID)
    assert f"События {site.name}" == cal['X-WR-CALNAME']
    # Create some content
    nces = EventFactory.create_batch(3)
    response = client.get(url)
    cal = Calendar.from_ical(response.content)
    assert set(nce.name for nce in nces) == set(evt['SUMMARY']
                                                for evt in cal.subcomponents
                                                if isinstance(evt, Event))
