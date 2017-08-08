import datetime

import pytest
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_bytes
from django.utils.translation import ugettext as _

from learning.factories import SemesterFactory, CourseOfferingFactory, \
    AssignmentFactory, EnrollmentFactory, CourseOfferingNewsFactory
from learning.models import Enrollment, StudentAssignment, \
    AssignmentNotification, CourseOfferingNewsNotification
from users.factories import UserFactory, StudentCenterFactory


# TODO: TimetableStudentView - есть фильтр по enrolled_students, туда может попадать лишнее сейчас
# TODO: Убедиться, что в *.ical они тоже не попадают (see CalendarStudentView also)
# TODO: Добавить тест о том, что не могут записаться в чужом городе


# Workaround to use Django's assertRedirects()
STS = SimpleTestCase()


@pytest.mark.skip('not implemented')
def test_enrollment_for_club_students(self):
    """ Club Student can enroll only on open courses """
    pass


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
    current_semester.enroll_before = (today - datetime.timedelta(days=1)).date()
    current_semester.save()
    response = client.post(co.get_enroll_url(), form)
    assert response.status_code == 403
    current_semester.enroll_before = (today + datetime.timedelta(days=1)).date()
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
    assert len(response.context['course_list_available']) == 0
    assert len(response.context['enrollments_ongoing']) == 1
    assert len(response.context['enrollments_archive']) == 0
    # Check `back` url on unenroll action
    url = co.get_unenroll_url() + "?back=course_list_student"
    STS.assertRedirects(client.post(url, form),
                        reverse('course_list_student'))
    assert set(a_ss) == set(StudentAssignment.objects
                                  .filter(student=s,
                                          assignment__course_offering=co))
    # Check courses on student courses page are empty
    response = client.get(reverse("course_list_student"))
    assert len(response.context['course_list_available']) == 1
    assert len(response.context['enrollments_ongoing']) == 0
    assert len(response.context['enrollments_archive']) == 0


@pytest.mark.django_db
def test_enrollment_capacity(client):
    s = StudentCenterFactory(city_id='spb')
    current_semester = SemesterFactory.create_current()
    co = CourseOfferingFactory.create(semester=current_semester,
                                      is_open=True)
    co_url = co.get_absolute_url()
    client.login(s)
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
    s2 = StudentCenterFactory()
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
    current_semester.enroll_before = today.date()
    current_semester.save()
    co = CourseOfferingFactory.create(semester=current_semester)
    url = co.get_enroll_url()
    form = {'course_offering_pk': co.pk}
    response = client.post(url, form)
    assert response.status_code == 302
    # FIXME: Find how to assert redirects with pytest and Django
    # assert response.url == client.request.get_absolute_uri(co.get_absolute_url())
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
