import datetime

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_bytes
from django.utils.translation import ugettext as _

from learning.factories import SemesterFactory, CourseOfferingFactory, \
    AssignmentFactory, EnrollmentFactory, CourseOfferingNewsFactory
from learning.models import Enrollment, StudentAssignment, \
    AssignmentNotification, CourseOfferingNewsNotification
from learning.tests.utils import assert_redirects
from learning.utils import now_local
from users.factories import StudentCenterFactory, StudentClubFactory


# TODO: Убедиться, что в *.ical они тоже не попадают (see CalendarStudentView also)
# TODO: Test volunteer can enroll!


@pytest.mark.django_db
def test_enrollment_for_club_students(client):
    """ Club Student can enroll only on open courses """
    tomorrow = now_local('spb') + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(city_code='spb',
                                          enrollment_end_at=tomorrow.date())
    co = CourseOfferingFactory.create(city='spb', semester=term, is_open=False)
    assert co.enrollment_is_open
    student_center = StudentCenterFactory(city_id='spb')
    student_club = StudentClubFactory(city_id='spb')
    form = {'course_offering_pk': co.pk}
    client.login(student_center)
    response = client.post(co.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_club)
    response = client.post(co.get_enroll_url(), form)
    # Ok, club student can't login on center site
    assert response.status_code == 302


@pytest.mark.django_db
def test_unenrollment(client):
    s = StudentCenterFactory.create(city_id='spb')
    assert s.city_id is not None
    client.login(s)
    current_semester = SemesterFactory.create_current()
    co = CourseOfferingFactory.create(semester=current_semester, city='spb')
    as_ = AssignmentFactory.create_batch(3, course_offering=co)
    form = {'course_offering_pk': co.pk}
    # Enrollment already closed
    today = timezone.now()
    current_semester.enrollment_end_at = (today - datetime.timedelta(days=1)).date()
    current_semester.save()
    response = client.post(co.get_enroll_url(), form)
    assert response.status_code == 403
    current_semester.enrollment_end_at = (today + datetime.timedelta(days=1)).date()
    current_semester.save()
    response = client.post(co.get_enroll_url(), form, follow=True)
    assert response.status_code == 200
    assert Enrollment.objects.count() == 1
    response = client.get(co.get_absolute_url())
    assert smart_bytes("Unenroll") in response.content
    assert smart_bytes(co) in response.content
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    assert not enrollment.is_deleted
    client.post(co.get_unenroll_url(), form)
    assert Enrollment.active.filter(student=s, course_offering=co).count() == 0
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    enrollment_id = enrollment.pk
    assert enrollment.is_deleted
    # Make sure student progress won't been deleted
    a_ss = (StudentAssignment.objects.filter(student=s,
                                             assignment__course_offering=co))
    assert len(a_ss) == 3
    # On re-enroll use old record
    client.post(co.get_enroll_url(), form)
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    assert enrollment.pk == enrollment_id
    assert not enrollment.is_deleted
    # Check ongoing courses on student courses page are not empty
    response = client.get(reverse("course_list_student"))
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['ongoing_enrolled']) == 1
    assert len(response.context['archive_enrolled']) == 0
    # Check `back` url on unenroll action
    url = co.get_unenroll_url() + "?back=course_list_student"
    assert_redirects(client.post(url, form),
                     reverse('course_list_student'))
    assert set(a_ss) == set(StudentAssignment.objects
                                  .filter(student=s,
                                          assignment__course_offering=co))
    # Check courses on student courses page are empty
    response = client.get(reverse("course_list_student"))
    assert len(response.context['ongoing_rest']) == 1
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['archive_enrolled']) == 0


@pytest.mark.django_db
def test_enrollment_capacity(client):
    s = StudentCenterFactory(city_id='spb')
    client.login(s)
    current_semester = SemesterFactory.create_current()
    co = CourseOfferingFactory.create(city_id='spb',
                                      semester=current_semester,
                                      is_open=True)
    co_url = co.get_absolute_url()
    response = client.get(co_url)
    assert smart_bytes(_("Places available")) not in response.content
    assert smart_bytes(_("No places available")) not in response.content
    co.capacity = 1
    co.save()
    response = client.get(co_url)
    assert smart_bytes(_("Places available")) in response.content
    form = {'course_offering_pk': co.pk}
    client.post(co.get_enroll_url(), form)
    assert 1 == (Enrollment.active.filter(student=s, course_offering=co)
                 .count())
    # Capacity reached, show to second student nothing
    s2 = StudentCenterFactory(city_id='spb')
    client.login(s2)
    response = client.get(co_url)
    assert smart_bytes(_("No places available")) in response.content
    co.capacity = 2
    co.save()
    response = client.get(co_url)
    assert (smart_bytes(_("Places available")) + b": 1") in response.content


@pytest.mark.django_db
def test_enrollment(client):
    student = StudentCenterFactory.create(city_id='spb')
    client.login(student)
    today = timezone.now()
    current_semester = SemesterFactory.create_current()
    current_semester.enrollment_end_at = today.date()
    current_semester.save()
    co = CourseOfferingFactory.create(semester=current_semester)
    url = co.get_enroll_url()
    form = {'course_offering_pk': co.pk}
    response = client.post(url, form)
    assert response.status_code == 302
    assert 1 == (Enrollment.active
                      .filter(student=student, course_offering=co)
                      .count())
    as_ = AssignmentFactory.create_batch(3, course_offering=co)
    assert set((student.pk, a.pk) for a in as_) == set(StudentAssignment.objects
                          .filter(student=student)
                          .values_list('student', 'assignment'))
    co_other = CourseOfferingFactory.create(semester=current_semester)
    form.update({'back': 'course_list_student'})
    url = co_other.get_enroll_url()
    response = client.post(url, form)
    assert response.status_code == 302
    # assert response.url == reverse('course_list_student')
    # Try to enroll to old CO
    old_semester = SemesterFactory.create(year=2010)
    old_co = CourseOfferingFactory.create(semester=old_semester)
    form = {'course_offering_pk': old_co.pk}
    url = old_co.get_enroll_url()
    assert client.post(url, form).status_code == 403
    # If course offering has limited capacity and we reach it - reject request
    co.capacity = 1
    co.save()
    student2 = StudentCenterFactory.create(city_id='spb')
    client.login(student2)
    form = {'course_offering_pk': co.pk}
    client.post(url, form, follow=True)
    assert co.enrollment_set.count() == 1
    co.capacity = 2
    co.save()
    client.post(url, form, follow=True)
    assert co.enrollment_set.count() == 2


@pytest.mark.django_db
def test_assignments(client):
    """Create assignments for active enrollments only"""
    ss = StudentCenterFactory.create_batch(3)
    current_semester = SemesterFactory.create_current()
    co = CourseOfferingFactory.create(semester=current_semester)
    for student in ss:
        enrollment = EnrollmentFactory.create(student=student,
                                              course_offering=co)
    assert Enrollment.objects.count() == 3
    assert StudentAssignment.objects.count() == 0
    assignment = AssignmentFactory.create(course_offering=co)
    assert StudentAssignment.objects.count() == 3
    enrollment.is_deleted = True
    enrollment.save()
    assignment = AssignmentFactory.create(course_offering=co)
    assert StudentAssignment.objects.count() == 5
    assert StudentAssignment.objects.filter(student=enrollment.student,
                                            assignment=assignment).count() == 0
    # Check deadline notifications sent for active enrollments only
    AssignmentNotification.objects.all().delete()
    assignment.deadline_at = assignment.deadline_at - datetime.timedelta(days=1)
    assignment.save()
    active_students = Enrollment.active.count()
    assert active_students == 2
    assert AssignmentNotification.objects.count() == active_students
    CourseOfferingNewsNotification.objects.all().delete()
    assert CourseOfferingNewsNotification.objects.count() == 0
    CourseOfferingNewsFactory.create(course_offering=co)
    assert CourseOfferingNewsNotification.objects.count() == active_students


@pytest.mark.django_db
def test_reenrollment(client):
    """Create assignments for student if they left the course and come back"""
    s = StudentCenterFactory(city_id='spb')
    assignment = AssignmentFactory(course_offering__is_open=True,
                                   course_offering__city_id='spb')
    co = assignment.course_offering
    e = EnrollmentFactory(student=s, course_offering=co)
    assert not e.is_deleted
    assert StudentAssignment.objects.filter(student_id=s.pk).count() == 1
    e.is_deleted = True
    e.save()
    assignment2 = AssignmentFactory(course_offering=co)
    assert StudentAssignment.objects.filter(student_id=s.pk).count() == 1
    client.login(s)
    form = {'course_offering_pk': co.pk}
    response = client.post(co.get_enroll_url(), form, follow=True)
    assert response.status_code == 200
    e.refresh_from_db()
    assert StudentAssignment.objects.filter(student_id=s.pk).count() == 2


@pytest.mark.django_db
def test_enrollment_in_other_city(client):
    tomorrow = now_local('spb') + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(enrollment_end_at=tomorrow.date())
    co_spb = CourseOfferingFactory(city='spb', semester=term, is_open=False)
    assert co_spb.enrollment_is_open
    student_spb = StudentCenterFactory(city_id='spb')
    student_nsk = StudentCenterFactory(city_id='nsk')
    form = {'course_offering_pk': co_spb.pk}
    client.login(student_spb)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_nsk)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 403
    assert Enrollment.objects.count() == 1
    student = StudentCenterFactory(city_id=None)
    client.login(student)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert response.url == '/'
    assert Enrollment.objects.count() == 1
    # Check button visibility
    Enrollment.objects.all().delete()
    client.login(student_spb)
    response = client.get(co_spb.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    buttons = html.find("div", {"class": "o-buttons-vertical"}).find_all('button')
    assert any("Enroll in" in s.text for s in buttons)
    for user in [student_nsk, student]:
        client.login(user)
        response = client.get(co_spb.get_absolute_url())
        assert smart_bytes("Enroll in") not in response.content


@pytest.mark.django_db
def test_correspondence_courses(client):
    """Make sure students from any city can enroll in online course"""
    tomorrow = now_local('spb') + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(enrollment_end_at=tomorrow.date())
    co_spb = CourseOfferingFactory(city_id='spb',
                                   semester=term,
                                   is_open=False,
                                   is_correspondence=True)
    assert co_spb.enrollment_is_open
    student_spb = StudentCenterFactory(city_id='spb')
    student_nsk = StudentCenterFactory(city_id='nsk')
    form = {'course_offering_pk': co_spb.pk}
    client.login(student_spb)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_nsk)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 2


@pytest.mark.django_db
def test_enrollment_is_enrollment_open(client):
    today = now_local('spb')
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(city_code='spb',
                                          enrollment_end_at=today.date())
    co_spb = CourseOfferingFactory(city='spb', semester=term, is_open=False,
                                   completed_at=tomorrow.date())
    assert co_spb.enrollment_is_open
    student_spb = StudentCenterFactory(city_id='spb')
    client.login(student_spb)
    response = client.get(co_spb.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    buttons = html.find("div", {"class": "o-buttons-vertical"}).find_all('button')
    assert any("Enroll in" in s.text for s in buttons)
    default_completed_at = co_spb.completed_at
    co_spb.completed_at = today.date()
    co_spb.save()
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") not in response.content
    co_spb.completed_at = default_completed_at
    co_spb.save()
    assert co_spb.enrollment_is_open
    term.enrollment_start_at = today.date()
    term.save()
    assert co_spb.enrollment_is_open
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") in response.content
    # What if enrollment not stated yet
    term.enrollment_start_at = tomorrow.date()
    term.enrollment_end_at = tomorrow.date()
    term.save()
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") not in response.content
    # Already completed
    term.enrollment_start_at = yesterday.date()
    term.enrollment_end_at = yesterday.date()
    term.save()
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") not in response.content


